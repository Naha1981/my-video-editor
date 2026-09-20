from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STOCK_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
ALLOWED_INTENTS = {
    "hero_food",
    "craft",
    "experience",
    "proof",
    "cta",
    "problem",
    "result",
}


def _sidecar(media_path: Path) -> Path:
    return media_path.with_suffix(media_path.suffix + ".stock.json")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "approved"}


def register_stock_asset(
    media_path: Path,
    *,
    beat: str,
    intent: str,
    provider: str = "",
    source_url: str = "",
    license_name: str = "",
    attribution: str = "",
    approved: bool = False,
) -> dict[str, Any]:
    """Persist provenance for an explicitly attached stock asset."""
    suffix = media_path.suffix.lower()
    if suffix not in STOCK_SUFFIXES:
        raise ValueError(f"Unsupported stock video type: {suffix}")
    intent = str(intent or "").strip()
    if intent not in ALLOWED_INTENTS:
        raise ValueError(f"Unsupported stock intent: {intent}")
    beat = str(beat or "").strip() or intent
    payload = {
        "kind": "stock",
        "beat": beat,
        "intent": intent,
        "provider": str(provider or "").strip(),
        "source_url": str(source_url or "").strip(),
        "license_name": str(license_name or "").strip(),
        "attribution": str(attribution or "").strip(),
        "approved": _as_bool(approved),
        "provenance_status": "approved" if _as_bool(approved) else "pending",
    }
    _sidecar(media_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def read_stock_asset(media_path: Path) -> dict[str, Any] | None:
    sidecar = _sidecar(media_path)
    if not sidecar.exists():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if payload.get("kind") == "stock" else None


def enrich_analysis_with_stock(
    analysis: dict[str, Any] | None,
    media_path: Path,
) -> dict[str, Any]:
    """Attach stock provenance to analysis without changing semantic evidence."""
    analysis = dict(analysis or {})
    stock = read_stock_asset(media_path)
    if stock:
        analysis["stock"] = stock
    return analysis


def stock_public(
    asset_id: str,
    filename: str,
    media_path: Path,
    meta: dict[str, Any],
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    stock = (analysis or {}).get("stock") or read_stock_asset(media_path) or {}
    return {
        "id": asset_id,
        "filename": filename,
        "kind": "stock",
        "duration": meta.get("duration", 0),
        "width": meta.get("width", 0),
        "height": meta.get("height", 0),
        "fps": meta.get("fps", 0),
        "approved": bool(stock.get("approved")),
        "intent": stock.get("intent"),
        "beat": stock.get("beat"),
        "provider": stock.get("provider"),
        "source_url": stock.get("source_url"),
        "license_name": stock.get("license_name"),
        "attribution": stock.get("attribution"),
        "provenance_status": stock.get("provenance_status", "pending"),
        "analysis": analysis or {},
    }
