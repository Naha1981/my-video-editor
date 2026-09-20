from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from typing import Any

import cv2
import numpy as np

from .transcription import transcribe
from .vision import semantic_analyze, semantic_analyze_window
from .beats import detect_beats


def _ffmpeg_extract_frames(path: Path, fps: float = 2.0, width: int = 320):
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(path), "-vf",
        f"fps={fps},scale={width}:-2:force_original_aspect_ratio=decrease",
        "-f", "image2pipe", "-vcodec", "mjpeg", "-"
    ]
    p = subprocess.run(cmd, capture_output=True, timeout=120)
    if p.returncode != 0:
        return [], 0.0
    frames = []
    data = p.stdout
    start = 0
    while True:
        soi = data.find(b"\xff\xd8", start)
        if soi < 0:
            break
        eoi = data.find(b"\xff\xd9", soi + 2)
        if eoi < 0:
            break
        frame = cv2.imdecode(
            np.frombuffer(data[soi:eoi + 2], dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        if frame is not None:
            frames.append(frame)
        start = eoi + 2
    return frames, fps


def _frame_features(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    brightness = float(np.mean(gray) / 255)
    contrast = float(np.std(gray) / 128)
    saturation = float(np.mean(hsv[:, :, 1]) / 255)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    exposure = max(0, 1 - abs(brightness - .5) * 1.6)
    detail = min(1, sharpness / 350)
    quality = .35 * exposure + .25 * min(1, contrast) + .20 * saturation + .20 * detail
    return {
        "brightness": round(brightness, 4),
        "contrast": round(contrast, 4),
        "saturation": round(saturation, 4),
        "sharpness": round(sharpness, 2),
        "quality": round(quality * 100, 2),
    }


def _hist(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0, 1], None, [24, 16], [0, 180, 0, 256])
    cv2.normalize(h, h)
    return h


def ffprobe_duration(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, timeout=30)
    return max(0.0, float(p.stdout.strip() or 0))


def analyze_video(path: Path) -> dict[str, Any]:
    frames, sample_fps = _ffmpeg_extract_frames(path)
    if not frames:
        return {
            "sample_count": 0, "visual_score": 50.0, "hero_time": 0.0,
            "scene_changes": [], "scenes": 1, "features": {}, "semantic": {},
        }
    features = [_frame_features(f) for f in frames]
    q = [f["quality"] for f in features]
    hero_idx = int(np.argmax(q))
    changes = []
    previous = _hist(frames[0])
    for idx, frame in enumerate(frames[1:], start=1):
        corr = float(cv2.compareHist(previous, _hist(frame), cv2.HISTCMP_CORREL))
        if corr < .45:
            t = idx / sample_fps
            if not changes or t - changes[-1] >= .75:
                changes.append(round(t, 3))
        previous = _hist(frame)
    avg = {
        k: round(float(np.mean([f[k] for f in features])), 4)
        for k in ("brightness", "contrast", "saturation", "sharpness", "quality")
    }
    semantic = semantic_analyze(path)
    semantic_windows = []
    boundaries = [0.0] + changes
    try:
        total_duration = float(ffprobe_duration(path))
    except Exception:
        total_duration = len(frames) / sample_fps
    boundaries.append(max(boundaries[-1], total_duration))
    if semantic.get("enabled"):
        for index in range(len(boundaries) - 1):
            start, end = boundaries[index], boundaries[index + 1]
            if end - start >= 0.5:
                window = semantic_analyze_window(path, start, end, max_frames=6)
                window["shot_index"] = index
                semantic_windows.append(window)
    return {
        "sample_count": len(frames),
        "sample_fps": sample_fps,
        "visual_score": avg["quality"],
        "hero_time": round(hero_idx / sample_fps, 3),
        "scene_changes": changes,
        "scenes": len(changes) + 1,
        "features": avg,
        "semantic": semantic,
        "semantic_windows": semantic_windows,
    }


def _extract_mono_wav(path: Path, seconds: float | None = None) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000"]
    if seconds is not None:
        cmd += ["-t", str(seconds)]
    cmd += [tmp.name]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        Path(tmp.name).unlink(missing_ok=True)
        raise RuntimeError(p.stderr.strip() or "Audio extraction failed")
    return Path(tmp.name)


def detect_active_audio(path: Path, sample_rate: int = 16000, hop_seconds: float = .20) -> dict[str, Any]:
    import os
    if os.getenv("NAHAVIDEO_ENABLE_AUDIO_INTELLIGENCE", "1").lower() in {"0", "false", "no", "off"}:
        return {"available": False, "active_ranges": [], "silence_ratio": 0.0, "reason": "audio intelligence disabled"}
    try:
        import librosa
    except Exception:
        return {"available": False, "active_ranges": [], "silence_ratio": 0.0}
    wav = _extract_mono_wav(path)
    try:
        y, sr = librosa.load(str(wav), sr=sample_rate, mono=True)
    finally:
        wav.unlink(missing_ok=True)
    if y.size == 0:
        return {"available": True, "active_ranges": [], "silence_ratio": 1.0}
    hop = max(1, int(hop_seconds * sr))
    frame = max(hop * 4, 1024)
    rms = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop, center=True)[0]
    db = librosa.amplitude_to_db(np.maximum(rms, 1e-8), ref=np.max)
    threshold = min(-18.0, max(-42.0, float(np.percentile(db, 25) + 6.0)))
    active = db > threshold
    ranges = []
    start = None
    for i, is_active in enumerate(active):
        t = i * hop / sr
        if is_active and start is None:
            start = t
        elif not is_active and start is not None:
            if t - start >= .35:
                ranges.append([round(start, 3), round(t, 3)])
            start = None
    if start is not None:
        ranges.append([round(start, 3), round(len(y) / sr, 3)])
    return {
        "available": True,
        "threshold_db": round(threshold, 2),
        "active_ranges": ranges,
        "silence_ratio": round(float(1 - np.count_nonzero(active) / max(len(active), 1)), 4),
    }


def analyze_audio_intelligence(path: Path) -> dict[str, Any]:
    try:
        audio = detect_active_audio(path)
    except Exception as exc:
        audio = {
            "available": False, "active_ranges": [], "silence_ratio": 0.0,
            "reason": f"audio analysis error: {type(exc).__name__}: {exc}",
        }
    transcript = transcribe(path)
    beats = detect_beats(path)
    return {"audio": {**audio, "beats": beats}, "transcript": transcript}
