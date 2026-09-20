from __future__ import annotations
from pathlib import Path
from typing import Any, Callable


def render_brand_card(
    temp: Path,
    duration: float,
    logo: Path | None = None,
    engine: Callable[..., Path] | None = None,
    context: dict[str, Any] | None = None,
) -> Path:
    """Render a NahaLabs motion brand card through the supplied engine or FFmpeg fallback.

    The engine seam is intentionally dependency-free: the proprietary motion renderer can
    later be injected without changing the Director or media pipeline.
    """
    payload = {
        "brand": "NahaLabs",
        "product": "NahaVideo AI Director",
        "format": {"width": 1080, "height": 1920, "fps": 30},
        "duration": float(duration),
        "logo": str(logo) if logo else None,
        **(context or {}),
    }
    if engine:
        result = engine(temp=temp, duration=duration, logo=logo, context=payload)
        if not isinstance(result, Path):
            result = Path(result)
        if not result.exists():
            raise RuntimeError("NahaLabs motion engine returned a missing output")
        return result

    from .media import _write_logo_card
    return _write_logo_card(temp, duration, logo)
