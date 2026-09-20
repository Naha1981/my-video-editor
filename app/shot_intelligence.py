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
    return {"tags": list(dict.fromkeys(tags)), "confidence": round(min(1.0, max([float(v or 0) for v in labels.values()] or [0.0])), 3)}


def intent_fit(analysis: dict[str, Any] | None, intent: str) -> float:
    labels = (analysis or {}).get("semantic", {}).get("labels", {}) or {}
    wanted = INTENT_LABELS.get(intent, [intent])
    return round(max((float(labels.get(label, 0) or 0) for label in wanted), default=0.0), 3)
