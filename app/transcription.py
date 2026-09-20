from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_MODEL = None
_MODEL_KEY = None


def _merge_ranges(ranges: list[list[float]], gap: float = 0.18) -> list[list[float]]:
    if not ranges:
        return []
    ordered = sorted((float(a), float(b)) for a, b in ranges if b > a)
    merged: list[list[float]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start - merged[-1][1] <= gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [[round(a, 3), round(b, 3)] for a, b in merged]


def _word_dict(word: Any) -> dict[str, Any]:
    return {
        "start": round(float(getattr(word, "start", 0.0) or 0.0), 3),
        "end": round(float(getattr(word, "end", 0.0) or 0.0), 3),
        "word": str(getattr(word, "word", "") or "").strip(),
    }


def transcribe(path: Path) -> dict[str, Any]:
    global _MODEL, _MODEL_KEY
    enabled = os.getenv("NAHAVIDEO_ENABLE_TRANSCRIBE", "0").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return {"available": False, "enabled": False, "segments": [], "speech_ranges": [], "reason": "disabled"}

    try:
        from faster_whisper import WhisperModel
    except Exception:
        return {
            "available": False,
            "enabled": True,
            "segments": [],
            "speech_ranges": [],
            "reason": "faster-whisper is not installed",
        }

    model_size = os.getenv("NAHAVIDEO_WHISPER_MODEL", "tiny")
    device = os.getenv("NAHAVIDEO_WHISPER_DEVICE", "cpu")
    compute_type = os.getenv("NAHAVIDEO_WHISPER_COMPUTE", "int8")
    key = (model_size, device, compute_type)
    if _MODEL is None or _MODEL_KEY != key:
        _MODEL = WhisperModel(model_size, device=device, compute_type=compute_type)
        _MODEL_KEY = key

    segments_iter, info = _MODEL.transcribe(
        str(path),
        beam_size=1,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
    )

    segments: list[dict[str, Any]] = []
    speech_ranges: list[list[float]] = []
    for seg in segments_iter:
        words = [_word_dict(w) for w in (getattr(seg, "words", None) or [])]
        start = float(getattr(seg, "start", 0.0) or 0.0)
        end = float(getattr(seg, "end", start) or start)
        text = str(getattr(seg, "text", "") or "").strip()
        if end <= start and not words:
            continue
        if words:
            start = min(start, words[0]["start"])
            end = max(end, words[-1]["end"])
        segments.append({"start": round(start, 3), "end": round(end, 3), "text": text, "words": words})
        speech_ranges.append([start, end])

    return {
        "available": True,
        "enabled": True,
        "language": getattr(info, "language", None),
        "language_probability": round(float(getattr(info, "language_probability", 0.0) or 0.0), 4),
        "segments": segments,
        "speech_ranges": _merge_ranges(speech_ranges),
        "reason": "local faster-whisper transcript",
    }
