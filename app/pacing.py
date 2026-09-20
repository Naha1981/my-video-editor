from __future__ import annotations

from typing import Any


BASE = {
    "energetic": {"hook": 1.8, "build": 1.7, "craft": 1.8, "experience": 2.0, "proof": 1.8, "cta": 1.6},
    "balanced": {"hook": 2.5, "build": 2.5, "craft": 2.5, "experience": 3.0, "proof": 2.5, "cta": 2.2},
}


def target_duration(intent: str, pace: str, fit: float = 0.0) -> float:
    table = BASE.get(pace, BASE["balanced"])
    key = intent if intent in table else "build"
    value = table[key]
    # Strong semantic matches can breathe slightly; weak matches stay tighter.
    return round(value * (0.9 + min(0.15, max(0.0, fit) * 0.15)), 3)


def apply_pacing(
    timeline: list[dict[str, Any]],
    total_duration: float,
    pace: str = "balanced",
) -> list[dict[str, Any]]:
    """Allocate screen time by creative beat while respecting the final duration."""
    if not timeline:
        return timeline
    budget = max(0.0, float(total_duration))
    targets = [
        min(float(item.get("duration", 0)), target_duration(
            str(item.get("creative_intent", "build")),
            pace,
            float(item.get("intent_fit", 0) or 0),
        ))
        for item in timeline
    ]
    if sum(targets) > budget and sum(targets) > 0:
        scale = budget / sum(targets)
        targets = [x * scale for x in targets]
    else:
        spare = budget - sum(targets)
        # Give spare time to proof/experience before stretching the hook/CTA.
        order = sorted(
            range(len(timeline)),
            key=lambda i: (
                0 if timeline[i].get("creative_intent") in {"proof", "experience", "craft"} else 1,
                -float(timeline[i].get("intent_fit", 0) or 0),
            ),
        )
        for i in order:
            if spare <= 0:
                break
            cap = max(targets[i], min(4.0, float(timeline[i].get("duration", 0))))
            add = min(spare, max(0.0, cap - targets[i]))
            targets[i] += add
            spare -= add

    for item, duration in zip(timeline, targets):
        item["duration"] = round(max(0.6, duration), 3)
    return timeline
