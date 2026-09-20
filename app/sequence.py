from __future__ import annotations

from typing import Any

from .shot_intelligence import intent_fit


def build_story_sequence(
    scored: list[dict[str, Any]],
    creative_direction: dict[str, Any] | None = None,
    max_duration: float = 30.0,
    max_per_clip: float = 4.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Construct an ordered commercial narrative from creative shot intents.

    Required intents are preferred first/last; supporting intents fill the middle.
    Each source clip is used at most once.
    """
    selected = (creative_direction or {}).get("selected", {}) or {}
    sequence = [str(x) for x in selected.get("shot_sequence", [])]
    if not sequence:
        sequence = ["hero_food", "craft", "experience", "proof", "cta"]

    # Treat first and last beats as structural requirements.
    required = set(sequence[:1] + sequence[-1:])
    candidates = [x for x in scored if x.get("clip") is not None]
    used: set[str] = set()
    timeline: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    remaining = float(max_duration)

    def choose(intent: str) -> dict[str, Any] | None:
        ranked = []
        for item in candidates:
            clip = item["clip"]
            if clip.id in used:
                continue
            fit = intent_fit(clip.analysis or {}, intent)
            base = float(item.get("score", 0))
            ranked.append((fit, base, item))
        if not ranked:
            return None
        ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
        fit, base, item = ranked[0]
        # Don't force a weak semantic match when there is no evidence, except
        # for structural fallback beats where the overall shot score is useful.
        if fit <= 0 and intent not in required:
            return None
        return {"item": item, "fit": fit, "base": base}

    for index, intent in enumerate(sequence):
        if remaining < 0.6:
            break
        chosen = choose(intent)
        if not chosen:
            decisions.append({
                "step": index + 1,
                "intent": intent,
                "status": "unfilled",
                "reason": "No unused source clip matched this creative intent.",
            })
            continue

        item = chosen["item"]
        clip = item["clip"]
        duration = min(float(max_per_clip), remaining, max(0.6, float(clip.duration)))
        timeline.append({
            "id": f"cut_{len(timeline) + 1}",
            "type": "clip",
            "enabled": True,
            "clip_id": clip.id,
            "filename": clip.filename,
            "creative_intent": intent,
            "intent_fit": round(chosen["fit"], 3),
            "duration": round(duration, 3),
            "score": item.get("score", 0),
            "reasons": list(item.get("reasons", [])) + [
                f"selected for {intent} ({chosen['fit'] * 100:.0f}% intent fit)"
            ],
        })
        used.add(clip.id)
        remaining -= duration
        decisions.append({
            "step": index + 1,
            "intent": intent,
            "status": "selected",
            "clip_id": clip.id,
            "filename": clip.filename,
            "intent_fit": round(chosen["fit"], 3),
            "reason": f"Highest available creative fit for {intent}.",
        })

    # If no semantic sequence could be built, preserve the strongest ranked clip.
    if not timeline and candidates and remaining >= 0.6:
        item = candidates[0]
        clip = item["clip"]
        duration = min(float(max_per_clip), remaining, max(0.6, float(clip.duration)))
        timeline.append({
            "id": "cut_1",
            "type": "clip",
            "enabled": True,
            "clip_id": clip.id,
            "filename": clip.filename,
            "creative_intent": "fallback",
            "intent_fit": 0.0,
            "duration": round(duration, 3),
            "score": item.get("score", 0),
            "reasons": list(item.get("reasons", [])) + ["sequence fallback to strongest ranked shot"],
        })
        decisions.append({
            "step": 1,
            "intent": "fallback",
            "status": "selected",
            "clip_id": clip.id,
            "filename": clip.filename,
            "intent_fit": 0.0,
            "reason": "No creative-semantic match was available; used strongest ranked shot.",
        })

    return timeline, decisions
