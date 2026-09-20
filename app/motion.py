from __future__ import annotations
from pathlib import Path
from typing import Any, Callable


def render_brand_card(temp: Path, duration: float, logo: Path | None = None, engine: Callable[..., Path] | None = None, context: dict[str, Any] | None = None) -> Path:
    """Brand-motion seam. A supplied NahaLabs motion engine can replace the FFmpeg fallback."""
    if engine:
        return engine(temp=temp, duration=duration, logo=logo, context=context or {})
    from .media import _write_logo_card
    return _write_logo_card(temp, duration, logo)
