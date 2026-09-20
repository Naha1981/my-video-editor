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


def validate_final_plan(
    plan: dict[str, Any],
    clips: dict[str, Path],
    *,
    approved_stock_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Production gate: return explicit blockers/warnings before final rendering."""
    timeline = [x for x in plan.get("timeline", []) if x.get("enabled", True) is not False]
    checks: list[dict[str, Any]] = []
    approved = approved_stock_ids or set()

    required_gaps = int((plan.get("footage_gaps") or {}).get("required_gap_count", 0) or 0)
    checks.append({
        "id": "required_coverage",
        "status": "pass" if required_gaps == 0 else "block",
        "message": "All required creative beats are covered." if required_gaps == 0 else f"{required_gaps} required footage gap(s) remain.",
    })

    missing = [x for x in timeline if x.get("type") == "clip" and x.get("clip_id") not in clips]
    checks.append({
        "id": "source_files",
        "status": "pass" if not missing else "block",
        "message": "All timeline source files exist." if not missing else f"{len(missing)} timeline source file(s) are missing.",
    })

    pending = []
    for item in timeline:
        if item.get("type") != "clip":
            continue
        clip = clips.get(item.get("clip_id"))
        if not clip:
            continue
        stock = (item.get("stock") or {})
        sidecar = clip.with_suffix(clip.suffix + ".stock.json")
        if sidecar.exists():
            try:
                import json
                stock = json.loads(sidecar.read_text(encoding="utf-8"))
            except Exception:
                stock = {}
        if stock.get("kind") == "stock" and (not stock.get("approved") or item.get("clip_id") not in approved):
            pending.append(item.get("clip_id"))
    checks.append({
        "id": "stock_approval",
        "status": "pass" if not pending else "block",
        "message": "All stock in the final timeline is approved." if not pending else f"{len(set(pending))} stock asset(s) are pending approval.",
    })

    provenance_missing = []
    for cid in set(pending):
        pass
    for item in timeline:
        if item.get("type") != "clip":
            continue
        clip = clips.get(item.get("clip_id"))
        if not clip:
            continue
        sidecar = clip.with_suffix(clip.suffix + ".stock.json")
        if sidecar.exists():
            try:
                import json
                stock = json.loads(sidecar.read_text(encoding="utf-8"))
            except Exception:
                stock = {}
            if stock.get("kind") == "stock" and (not stock.get("provider") or not stock.get("source_url")):
                provenance_missing.append(item.get("clip_id"))
    checks.append({
        "id": "stock_provenance",
        "status": "pass" if not provenance_missing else "block",
        "message": "Stock provenance is complete." if not provenance_missing else f"{len(set(provenance_missing))} stock asset(s) lack provider/source provenance.",
    })

    duration = sum(float(x.get("duration", 0) or 0) for x in timeline)
    requested = float((plan.get("settings") or {}).get("duration", 0) or 0)
    duration_ok = requested <= 0 or (0.1 <= duration <= requested + 0.5)
    checks.append({
        "id": "timeline_duration",
        "status": "pass" if duration_ok else "block",
        "message": f"Timeline duration is {duration:.2f}s for a {requested:.2f}s request." if requested else f"Timeline duration is {duration:.2f}s.",
    })

    blocker_count = sum(x["status"] == "block" for x in checks)
    warning_count = sum(x["status"] == "warn" for x in checks)
    return {
        "status": "blocked" if blocker_count else ("warning" if warning_count else "ready"),
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "checks": checks,
    }
