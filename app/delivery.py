from __future__ import annotations

from pathlib import Path
from typing import Any

from .ffmpeg_skill import run_tool, available as ffmpeg_skill_available


PLATFORMS = {
    "reels": {"label": "Instagram Reels", "template": "reels", "aspect": "9:16"},
    "tiktok": {"label": "TikTok", "template": "tiktok", "aspect": "9:16"},
    "shorts": {"label": "YouTube Shorts", "template": "shorts", "aspect": "9:16"},
    "youtube": {"label": "YouTube", "template": "youtube", "aspect": "16:9"},
    "linkedin": {"label": "LinkedIn", "template": "linkedin", "aspect": "16:9"},
    "facebook": {"label": "Facebook", "template": "facebook", "aspect": "1:1"},
    "x": {"label": "X", "template": "x", "aspect": "16:9"},
    "podcast": {"label": "Podcast", "template": "podcast", "aspect": "16:9"},
}

ALIASES = {
    "instagram": "reels",
    "instagram_reel": "reels",
    "youtube_short": "shorts",
    "youtube_shorts": "shorts",
    "fb": "facebook",
    "twitter": "x",
}


def normalize_platforms(platforms: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in platforms or ["reels"]:
        key = ALIASES.get(str(raw).strip().lower(), str(raw).strip().lower())
        if key in PLATFORMS and key not in out:
            out.append(key)
    return out or ["reels"]


def build_delivery_pack(platforms: list[str] | None) -> dict[str, Any]:
    normalized = normalize_platforms(platforms)
    engine = "ffmpeg-skill" if ffmpeg_skill_available() else "native-ffmpeg"
    return {
        "status": "ready",
        "engine": engine,
        "platforms": [
            {
                "id": key,
                **PLATFORMS[key],
                "qa": "platform-check" if engine == "ffmpeg-skill" else "native-render-output-check",
            }
            for key in normalized
        ],
        "notes": [
            "All destinations share the same NahaVideo edit decision graph.",
            "Platform templates are used when ffmpeg-skill is installed.",
            "Without ffmpeg-skill, NahaVideo preserves the native renderer and makes the fallback explicit.",
        ],
    }


def render_delivery_pack(
    source: Path,
    output_dir: Path,
    platforms: list[str] | None,
) -> dict[str, Any]:
    normalized = normalize_platforms(platforms)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    if not source.exists():
        return {"status": "failed", "results": [], "reason": "source render missing"}

    if not ffmpeg_skill_available():
        return {
            "status": "fallback_only",
            "engine": "native-ffmpeg",
            "results": [],
            "reason": "ffmpeg-skill unavailable; base render is still available",
        }

    for key in normalized:
        spec = PLATFORMS[key]
        output = output_dir / f"{source.stem}_{key}{source.suffix}"
        result = run_tool(
            "render.py",
            ["--template", spec["template"], str(source), "-o", str(output), "--json"],
            timeout=300,
        )
        qa = None
        if output.exists():
            probe = run_tool("probe.py", [str(output), "--json"])
            check = run_tool("check.py", [str(output), "--platform", key, "--json"])
            qa = {
                "status": "verified" if probe.get("status") == "ok" and check.get("status") == "ok" else "failed",
                "probe": probe.get("data"),
                "check": check.get("data"),
            }
        results.append({
            "platform": key,
            "label": spec["label"],
            "output": str(output) if output.exists() else None,
            "status": result.get("status"),
            "result": result.get("data"),
            "error": result.get("stderr"),
            "qa": qa,
        })
    ok = all(x["status"] == "ok" and x["output"] and (x["qa"] or {}).get("status") == "verified" for x in results)
    return {
        "status": "complete" if ok else "partial",
        "engine": "ffmpeg-skill",
        "results": results,
    }
