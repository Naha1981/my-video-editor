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


def _inside_ranges(value: float, ranges: list[list[float]], padding: float = 0.0) -> bool:
    return any(float(start) - padding < value < float(end) + padding for start, end in ranges)


def align_cut_boundaries(
    timeline: list[dict[str, Any]],
    beat_times: list[float] | None = None,
    total_duration: float | None = None,
    tolerance: float = 0.28,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Move adjacent cut boundaries toward beats, but never knowingly through speech."""
    if len(timeline) < 2:
        return timeline, []

    beats = sorted(float(x) for x in (beat_times or []) if float(x) >= 0)
    budget = float(total_duration) if total_duration is not None else sum(float(x.get("duration", 0)) for x in timeline)
    decisions: list[dict[str, Any]] = []
    cursor = 0.0

    for index in range(len(timeline) - 1):
        current = timeline[index]
        following = timeline[index + 1]
        current_duration = float(current.get("duration", 0))
        following_duration = float(following.get("duration", 0))
        desired = cursor + current_duration
        if desired <= 0 or desired >= budget:
            cursor += current_duration
            continue

        candidates = [b for b in beats if abs(b - desired) <= tolerance and 0.6 <= b - cursor <= current_duration + following_duration - 0.6]
        safe = []
        current_speech = current.get("speech_ranges_output", []) or []
        next_speech = following.get("speech_ranges_output", []) or []
        for beat in candidates:
            if not _inside_ranges(beat, current_speech) and not _inside_ranges(beat, next_speech):
                safe.append(beat)

        target = min(safe, key=lambda b: abs(b - desired)) if safe else None
        if target is not None:
            delta = target - desired
            current["duration"] = round(current_duration + delta, 3)
            following["duration"] = round(following_duration - delta, 3)
            decisions.append({
                "boundary": index + 1,
                "status": "beat_aligned",
                "at": round(target, 3),
                "offset": round(delta, 3),
                "reason": "Moved cut to nearest safe music beat.",
            })
        elif _inside_ranges(desired, current_speech):
            edges = [float(end) for start, end in current_speech if float(start) < desired < float(end)]
            edge = min(edges, key=lambda x: abs(x - desired)) if edges else None
            if edge is not None and abs(edge - desired) <= tolerance and 0.6 <= edge - cursor <= current_duration + following_duration - 0.6:
                delta = edge - desired
                current["duration"] = round(current_duration + delta, 3)
                following["duration"] = round(following_duration - delta, 3)
                decisions.append({
                    "boundary": index + 1,
                    "status": "speech_safe",
                    "at": round(edge, 3),
                    "offset": round(delta, 3),
                    "reason": "Beat alignment was overridden to avoid cutting through dialogue.",
                })
            else:
                decisions.append({
                    "boundary": index + 1,
                    "status": "speech_preserved",
                    "at": round(desired, 3),
                    "reason": "No safe beat boundary was available near an active speech range.",
                })
        else:
            decisions.append({
                "boundary": index + 1,
                "status": "unchanged",
                "at": round(desired, 3),
                "reason": "No suitable beat within tolerance.",
            })
        cursor += float(current.get("duration", current_duration))

    return timeline, decisions
