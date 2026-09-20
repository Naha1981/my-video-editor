from __future__ import annotations

from typing import Any


def build_storyboard(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn an edit plan into explicit creative beats for the renderer/UI."""
    beats = []
    direction = plan.get("creative_direction", {}) or {}
    selected = direction.get("selected", {}) or {}
    sequence = selected.get("shot_sequence", [])
    active = [x for x in plan.get("timeline", []) if x.get("enabled", True)]
    for i, item in enumerate(active):
        if item.get("type") == "logo":
            beats.append({
                "beat": i + 1,
                "type": "brand_close",
                "creative_intent": "cta",
                "purpose": "brand recall",
                "visual": "NahaLabs logo/end card",
                "duration": item.get("duration", 2.0),
                "transition": "fade",
            })
            continue

        reasons = " ".join(item.get("reasons", [])).lower()
        intent = item.get("creative_intent") or (sequence[min(i, len(sequence) - 1)] if sequence else None)
        if i == 0:
            purpose = "hook"
            transition = "hard_cut"
        elif "speech" in reasons:
            purpose = "message"
            transition = "hard_cut"
        elif i == len(active) - 1:
            purpose = "payoff"
            transition = "hard_cut"
        else:
            purpose = "build"
            transition = "hard_cut"

        beats.append({
            "beat": i + 1,
            "type": purpose,
            "creative_intent": intent,
            "purpose": purpose,
            "visual": item.get("filename", "source clip"),
            "source_start": item.get("source_start", 0),
            "duration": item.get("duration", 0),
            "transition": transition,
            "caption": None,
            "intent_fit": item.get("intent_fit", 0),
            "selection_score": item.get("score", 0),
        })
    return beats


def add_transcript_captions(plan: dict[str, Any]) -> dict[str, Any]:
    """Attach short, timestamped captions to transcript-aware timeline items."""
    result = dict(plan)
    captions = []
    output_offset = 0.0
    for item in result.get("timeline", []):
        if item.get("enabled", True) is False:
            continue
        if item.get("type") != "clip":
            output_offset += float(item.get("duration", 0))
            continue
        source_start = float(item.get("source_start", 0))
        source_end = source_start + float(item.get("duration", 0))
        ranges = item.get("speech_ranges_source", [])
        # The transcript text itself is stored on the clip analysis and is
        # copied into the plan by the API when captions are requested.
        for segment in item.get("transcript_segments_source", []):
            start = float(segment.get("start", 0))
            end = float(segment.get("end", start))
            if end <= source_start or start >= source_end:
                continue
            captions.append({
                "start": round(output_offset + max(start, source_start) - source_start, 3),
                "end": round(output_offset + min(end, source_end) - source_start, 3),
                "text": str(segment.get("text", "")).strip(),
            })
        output_offset += float(item.get("duration", 0))
    result["captions"] = [x for x in captions if x["text"]]
    return result
