from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

from .focal import focal_point, crop_filter

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
                    "-t", str(duration), "-vf", crop_filter(width, height, focal),
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
    }
