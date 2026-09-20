from __future__ import annotations

from typing import Any


INTENT_LABELS = {
    "hero_food": ["food", "product"],
    "craft": ["chef", "food"],
    "experience": ["experience", "person"],
    "proof": ["product", "experience"],
    "result": ["product", "food"],
    "cta": ["exterior", "product"],
}


def classify_shot(analysis: dict[str, Any] | None) -> dict[str, Any]:
    """Convert available semantic/visual evidence into explainable shot tags."""
    analysis = analysis or {}
    labels = analysis.get("semantic", {}).get("labels", {}) or {}
    visual = analysis.get("visual", {}) or {}
    stock = analysis.get("stock", {}) or {}
    tags: list[str] = []
    if labels:
        for name, value in sorted(labels.items(), key=lambda x: float(x[1] or 0), reverse=True):
            if float(value or 0) >= 0.12:
                tags.append(str(name))
    if visual.get("close_up"):
        tags.append("close_up")
    if visual.get("wide"):
        tags.append("wide")
    if analysis.get("hero_time") is not None:
        tags.append("hero_candidate")
    if stock.get("approved"):
        tags.append("approved_stock")
    return {
        "tags": list(dict.fromkeys(tags)),
        "confidence": round(min(1.0, max([float(v or 0) for v in labels.values()] or [0.0])), 3),
    }


def intent_fit(analysis: dict[str, Any] | None, intent: str) -> float:
    analysis = analysis or {}
    stock = analysis.get("stock", {}) or {}
    if stock.get("approved") and str(stock.get("intent", "")) == str(intent):
        return 1.0

    labels = analysis.get("semantic", {}).get("labels", {}) or {}
    wanted = INTENT_LABELS.get(intent, [intent])
    overall = max((float(labels.get(label, 0) or 0) for label in wanted), default=0.0)
    windows = analysis.get("semantic_windows", []) or []
    window_fit = max(
        (
            max((float((window.get("labels", {}) or {}).get(label, 0) or 0) for label in wanted), default=0.0)
            for window in windows
            if isinstance(window, dict)
        ),
        default=0.0,
    )
    return round(max(overall, window_fit), 3)
