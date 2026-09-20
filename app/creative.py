from __future__ import annotations

import re
from typing import Any


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def creative_direction(brief: dict[str, Any] | None = None, prompt: str = "") -> dict[str, Any]:
    brief = brief or {}
    corpus = _norm(" ".join([
        str(brief.get("category", "")),
        str(brief.get("offer", "")),
        str(brief.get("tone", "")),
        prompt,
    ])).lower()
    category = brief.get("category", "business")
    audience = brief.get("audience", "prospective customers")
    cta = brief.get("cta", "Learn more / enquire today")

    restaurant = category == "restaurant" or any(x in corpus for x in ["restaurant", "food", "dining", "menu", "chef"])
    fast = any(x in corpus for x in ["energetic", "fast", "punchy", "dynamic", "quick", "reel", "tiktok"])
    premium = any(x in corpus for x in ["premium", "luxury", "upscale", "cinematic", "exclusive"])

    if restaurant:
        concepts = [
            {
                "id": "sensory_hero",
                "name": "The Craving Cut",
                "hook": "Open on the most irresistible visual immediately.",
                "promise": "Make the viewer feel the food before asking them to act.",
                "proof": "Craft, texture, atmosphere and a real dining moment.",
                "cta": cta,
                "shot_sequence": ["hero_food", "craft", "detail", "experience", "cta"],
            },
            {
                "id": "experience",
                "name": "The Experience Cut",
                "hook": "Start with the feeling of being there.",
                "promise": "Show the meal as an experience, not just a product.",
                "proof": "People, space, service and signature food.",
                "cta": cta,
                "shot_sequence": ["experience", "hero_food", "craft", "proof", "cta"],
            },
            {
                "id": "signature",
                "name": "The Signature Cut",
                "hook": "Lead with the dish or moment the brand wants remembered.",
                "promise": "Build toward one unforgettable signature.",
                "proof": "Preparation, presentation and social atmosphere.",
                "cta": cta,
                "shot_sequence": ["hero_food", "craft", "proof", "experience", "cta"],
            },
        ]
        selected = concepts[2] if "signature" in corpus or "signature dish" in corpus else concepts[0]
    else:
        concepts = [
            {
                "id": "outcome",
                "name": "The Outcome Cut",
                "hook": "Open with the strongest end result.",
                "promise": "Show the value before explaining the mechanics.",
                "proof": "Product/service in use, evidence and human context.",
                "cta": cta,
                "shot_sequence": ["result", "context", "solution", "proof", "cta"],
            },
            {
                "id": "problem_solution",
                "name": "The Problem → Solution Cut",
                "hook": "Show the pain point the customer recognises.",
                "promise": "Move quickly from problem to useful solution.",
                "proof": "Real usage, process and outcome.",
                "cta": cta,
                "shot_sequence": ["problem", "solution", "proof", "result", "cta"],
            },
            {
                "id": "proof",
                "name": "The Proof Cut",
                "hook": "Lead with the most credible proof point.",
                "promise": "Build trust through evidence rather than hype.",
                "proof": "People, process, product and measurable/result visuals.",
                "cta": cta,
                "shot_sequence": ["proof", "solution", "context", "result", "cta"],
            },
        ]
        selected = concepts[1] if "problem" in corpus or "pain" in corpus else concepts[0]

    return {
        "selected": selected,
        "options": concepts,
        "category": "restaurant" if restaurant else "business",
        "audience": audience,
        "tone": brief.get("tone", "modern, clear, human"),
        "pacing": "energetic" if fast else ("cinematic" if premium else "balanced"),
        "creative_rule": "Show the strongest visual first; every beat must earn its place; finish with a single clear CTA.",
    }
