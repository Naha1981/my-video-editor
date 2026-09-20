from __future__ import annotations

from typing import Any

from .shot_intelligence import intent_fit


BEAT_INTENTS = {
    "hook": "hero_food",
    "craft": "craft",
    "experience": "experience",
    "proof": "proof",
    "cta": "cta",
    "problem": "problem",
    "solution": "result",
}

SEARCH_HINTS = {
    "hero_food": "premium hero food close-up",
    "craft": "chef preparation cooking detail",
    "experience": "real customers dining restaurant atmosphere",
    "proof": "signature dish restaurant interior location",
    "cta": "restaurant exterior storefront booking order",
    "problem": "customer problem business context",
    "result": "service in use successful outcome",
}


def _sequence(plan: dict[str, Any] | None) -> list[str]:
    direction = (plan or {}).get("creative_direction", {}) or {}
    selected = direction.get("selected", {}) or {}
    return [str(x) for x in selected.get("shot_sequence", [])]


def detect_footage_gaps(
    brief: dict[str, Any] | None,
    creative_direction: dict[str, Any] | None,
    timeline: list[dict[str, Any]] | None,
    clips: list[dict[str, Any]] | None,
    threshold: float = 0.35,
) -> dict[str, Any]:
    """Explain which required/supporting creative beats lack suitable footage."""
    brief = brief or {}
    direction = creative_direction or {}
    selected = direction.get("selected", {}) or {}
    sequence = [str(x) for x in selected.get("shot_sequence", [])]
    requirements = list(brief.get("shot_requirements", []) or [])

    if not requirements:
        category = brief.get("category", "business")
        if category == "restaurant":
            requirements = [
                {"beat": "hook", "need": "hero food/product close-up", "priority": "required"},
                {"beat": "craft", "need": "chef/preparation/detail", "priority": "supporting"},
                {"beat": "experience", "need": "real customer/dining atmosphere", "priority": "supporting"},
                {"beat": "proof", "need": "signature dish/service/location", "priority": "supporting"},
                {"beat": "cta", "need": "exterior, booking/order or brand shot", "priority": "required"},
            ]
        else:
            requirements = [
                {"beat": "hook", "need": "strongest product/service visual", "priority": "required"},
                {"beat": "problem", "need": "real customer/business context", "priority": "supporting"},
                {"beat": "solution", "need": "product/service in use", "priority": "supporting"},
                {"beat": "proof", "need": "result, people or environment", "priority": "supporting"},
                {"beat": "cta", "need": "brand, website or contact visual", "priority": "required"},
            ]

    timeline = [x for x in (timeline or []) if x.get("enabled", True) and x.get("type") == "clip"]
    clips = clips or []
    gaps = []
    coverage = []

    for req in requirements:
        beat = str(req.get("beat", ""))
        intent = BEAT_INTENTS.get(beat, beat)
        selected_matches = [x for x in timeline if str(x.get("creative_intent", "")) == intent]
        best = 0.0
        best_file = None
        for item in clips:
            analysis = item.get("analysis", {}) or {}
            fit = intent_fit(analysis, intent)
            if fit > best:
                best = fit
                best_file = item.get("filename")
        best = round(best, 3)
        state = "covered" if selected_matches else ("available" if best >= threshold else "missing")
        row = {
            "beat": beat,
            "intent": intent,
            "priority": req.get("priority", "supporting"),
            "need": req.get("need", ""),
            "status": state,
            "intent_fit": best,
            "available_filename": best_file,
            "search_hint": req.get("search_hint") or SEARCH_HINTS.get(intent, req.get("need", intent)),
        }
        coverage.append(row)
        if state == "missing":
            gaps.append(row)

    required_gaps = [x for x in gaps if x["priority"] == "required"]
    return {
        "status": "ready" if not gaps else "gaps_detected",
        "gap_count": len(gaps),
        "required_gap_count": len(required_gaps),
        "gaps": gaps,
        "coverage": coverage,
        "sequence": sequence,
        "notes": [
            "Gaps are based on available semantic evidence and the selected creative sequence.",
            "The Director does not invent footage; missing beats become explicit stock/B-roll requirements.",
        ],
    }
