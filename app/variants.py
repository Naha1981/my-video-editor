from __future__ import annotations

from pathlib import Path
from typing import Any
import subprocess

FORMATS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

def render_variants(source: Path, output_dir: Path, formats: list[str] | None = None) -> dict[str, Any]:
    if not source.exists():
        return {"status": "failed", "results": [], "reason": "source render missing"}
    selected = [x for x in (formats or list(FORMATS)) if x in FORMATS]
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for aspect in selected:
        width, height = FORMATS[aspect]
        slug = aspect.replace(":", "x")
        output = output_dir / f"{source.stem}_{slug}.mp4"
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1"
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-i", str(source),
            "-vf", vf, "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            str(output),
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if p.returncode == 0 and output.exists():
            results.append({"aspect": aspect, "width": width, "height": height, "output": str(output), "status": "complete"})
        else:
            results.append({"aspect": aspect, "width": width, "height": height, "output": None, "status": "failed", "error": p.stderr[-2000:]})
    return {
        "status": "complete" if results and all(x["status"] == "complete" for x in results) else "partial",
        "source": str(source),
        "results": results,
    }
