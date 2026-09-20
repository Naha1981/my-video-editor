from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

from .focal import focal_point, crop_filter



CAPTION_SAFE_ZONES = {
    "9:16": {"alignment": 2, "margin_v": 220, "font_size": 20},
    "1:1": {"alignment": 2, "margin_v": 110, "font_size": 18},
    "16:9": {"alignment": 2, "margin_v": 70, "font_size": 22},
}


def caption_safe_zone(aspect: str) -> dict[str, Any]:
    """Return conservative subtitle placement for each delivery aspect."""
    return dict(CAPTION_SAFE_ZONES.get(aspect, CAPTION_SAFE_ZONES["16:9"]))


def _write_srt(path: Path, captions: list[dict[str, Any]]) -> Path | None:
    if not captions:
        return None
    def ts(value: float) -> str:
        ms=max(0,int(round(float(value)*1000)))
        h,ms=divmod(ms,3600000); mi,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
        return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"
    lines=[]
    for i,item in enumerate(captions,1):
        text=str(item.get("text","")).strip().replace("\n"," ")
        if text:
            lines += [str(i), f"{ts(item.get('start',0))} --> {ts(item.get('end',0))}", text, ""]
    if not lines:
        return None
    path.write_text("\n".join(lines),encoding="utf-8")
    return path


def _subtitle_filter(path: Path, zone: dict[str, Any]) -> str:
    value=path.as_posix().replace("\\","/").replace(":","\\:").replace("'","\\'")
    return (
        f"subtitles='{value}':force_style='FontName=Arial,FontSize={zone['font_size']},"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,"
        f"Shadow=0,Alignment={zone['alignment']},MarginV={zone['margin_v']}'"
    )

FORMATS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}


def _run(cmd: list[str]) -> tuple[bool, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return p.returncode == 0, p.stderr[-2000:]


def render_variants(
    source: Path,
    output_dir: Path,
    formats: list[str] | None = None,
    timeline: list[dict[str, Any]] | None = None,
    captions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Render aspect variants, optionally reframing each Director timeline shot independently."""
    if not source.exists():
        return {"status": "failed", "results": [], "reason": "source render missing"}
    selected = [x for x in (formats or list(FORMATS)) if x in FORMATS]
    output_dir.mkdir(parents=True, exist_ok=True)
    segments = [
        x for x in (timeline or [])
        if x.get("enabled", True) is not False and x.get("type") == "clip"
    ]
    # A logo/end-card is already composed for the base render and remains centered.
    # When a timeline is supplied, source time boundaries are represented by cumulative durations.
    results = []
    for aspect in selected:
        width, height = FORMATS[aspect]
        slug = aspect.replace(":", "x")
        output = output_dir / f"{source.stem}_{slug}.mp4"
        focal_records = []
        zone = caption_safe_zone(aspect)
        srt = _write_srt(output_dir / f"{slug}_captions.srt", captions or [])
        part_paths = []
        cursor = 0.0
        work = output_dir / f"{slug}_parts"
        work.mkdir(exist_ok=True)
        if segments:
            for i, item in enumerate(segments):
                duration = max(0.05, float(item.get("duration", 0) or 0))
                focal = focal_point(source, cursor + min(0.05, duration / 2))
                focal_records.append({"index": i, "start": round(cursor, 3), "duration": round(duration, 3), **focal})
                part = work / f"part_{i:03d}.mp4"
                ok, err = _run([
                    "ffmpeg", "-y", "-v", "error", "-ss", str(cursor), "-i", str(source),
                    "-t", str(duration), "-vf", crop_filter(width, height, focal) + ("," + _subtitle_filter(srt, zone) if srt else ""),
                    "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", str(part),
                ])
                if not ok or not part.exists():
                    results.append({"aspect": aspect, "width": width, "height": height, "output": None, "status": "failed", "error": err, "focal": focal_records})
                    part_paths = []
                    break
                part_paths.append(part)
                cursor += duration
        else:
            focal = focal_point(source)
            focal_records.append(focal)
            part = work / "part_000.mp4"
            ok, err = _run([
                "ffmpeg", "-y", "-v", "error", "-i", str(source),
                "-vf", crop_filter(width, height, focal), "-r", "30",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", str(part),
            ])
            if ok and part.exists():
                part_paths.append(part)
            else:
                results.append({"aspect": aspect, "width": width, "height": height, "output": None, "status": "failed", "error": err, "focal": focal_records})
        if part_paths:
            concat = work / "concat.txt"
            def _concat_line(p: Path) -> str:
                safe = p.as_posix().replace("'", "'\\''")
                return f"file '{safe}'"
            concat.write_text("\n".join(_concat_line(p) for p in part_paths), encoding="utf-8")
            ok, err = _run([
                "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                "-i", str(concat), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", str(output),
            ])
            if ok and output.exists():
                results.append({"aspect": aspect, "width": width, "height": height, "output": str(output), "status": "complete", "focal": focal_records})
            else:
                results.append({"aspect": aspect, "width": width, "height": height, "output": None, "status": "failed", "error": err, "focal": focal_records})
    return {
        "status": "complete" if results and all(x["status"] == "complete" for x in results) else "partial",
        "source": str(source),
        "results": results,
        "reframing": "per-shot" if segments else "single-source",
        "caption_safe_zones": {aspect: caption_safe_zone(aspect) for aspect in selected},
    }
