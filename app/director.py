from dataclasses import dataclass, asdict
from typing import Any

from .shot_intelligence import intent_fit
from .sequence import build_story_sequence
from .pacing import apply_pacing

@dataclass
class Clip:
    id: str
    filename: str
    path: str
    duration: float
    width: int
    height: int
    fps: float
    analysis: dict[str, Any] | None = None

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("path", None)
        return data


def brief_settings(prompt: str, duration: int) -> dict[str, Any]:
    p = prompt.lower()
    style = "premium" if any(x in p for x in ["premium", "luxury", "upscale", "cinematic"]) else "social"
    pace = "energetic" if any(x in p for x in ["energetic", "fast", "punchy", "dynamic", "quick"]) else "balanced"
    wants_dialogue = any(x in p for x in ["dialogue", "voice", "speech", "talking", "interview"])
    logo = any(x in p for x in ["logo", "brand", "nahalabs", "end card"])
    food = any(x in p for x in ["food", "restaurant", "dish", "meal", "menu", "chef"])
    return {
        "duration": max(5, min(duration, 180)),
        "style": style,
        "pace": pace,
        "priority": "food" if food else "visual_story",
        "remove_dead_time": True,
        "music_ducking": wants_dialogue,
        "logo_ending": logo,
    }


def _semantic_relevance(clip: Clip, key: str, fallback: float = .0) -> float:
    semantic = (clip.analysis or {}).get("semantic", {})
    labels = semantic.get("labels", {})
    return float(labels.get(key, fallback) or fallback)


def score_clip(clip: Clip, settings: dict[str, Any], creative_direction: dict[str, Any] | None = None) -> tuple[float, list[str]]:
    name = clip.filename.lower()
    score = 50.0
    creative_direction = creative_direction or {}
    selected = creative_direction.get("selected", {}) or {}
    intent_text = " ".join(str(x) for x in selected.get("shot_sequence", []))
    reasons: list[str] = []
    if intent_text:
        hints = [x.replace("_", " ") for x in selected.get("shot_sequence", [])]
        hits = sum(1 for h in hints if h and any(part in name for part in h.split()))
        if hits:
            score += min(12, hits * 4)
            reasons.append("creative shot-intent filename signal")
    keyword_groups = {
        "food": ["food", "dish", "meal", "burger", "pizza", "steak", "dessert", "plate", "chef", "kitchen", "restaurant"],
        "people": ["person", "people", "customer", "guest", "waiter"],
        "hero": ["hero", "close", "closeup", "final", "best"],
    }

    analysis = clip.analysis or {}
    semantic = analysis.get("semantic", {}) or {}
    labels = semantic.get("labels", {}) or {}
    for intent in selected.get("shot_sequence", []):
        fit = intent_fit(analysis, str(intent))
        if fit > 0:
            score += min(10, fit * 12)
            reasons.append(f"visual intent fit {intent}: {fit * 100:.0f}%")

    for intent, label in {"hero_food":"food","craft":"chef","experience":"experience","proof":"product","result":"product","cta":"exterior"}.items():
        if intent in selected.get("shot_sequence", []) and label in labels:
            relevance=float(labels.get(label, 0) or 0)
            score += min(10, relevance * 18)
            if relevance > 0.08:
                reasons.append(f"AI {label} relevance {relevance * 100:.0f}% for {intent}")

    if settings["priority"] == "food":
        hits = sum(1 for k in keyword_groups["food"] if k in name)
        score += min(16, hits * 5)
        if hits:
            reasons.append("food-related filename signal")
        food_ai = _semantic_relevance(clip, "food")
        hero_ai = _semantic_relevance(clip, "hero")
        if food_ai:
            score += min(24, food_ai * 48)
            reasons.append(f"AI food relevance {food_ai * 100:.0f}%")
        if hero_ai:
            score += min(10, hero_ai * 20)
            reasons.append(f"AI hero-shot relevance {hero_ai * 100:.0f}%")

    if any(k in name for k in keyword_groups["hero"]):
        score += 8
        reasons.append("hero/close-up filename signal")

    analysis = clip.analysis or {}
    if analysis:
        visual = float(analysis.get("visual_score", 50.0))
        score += (visual - 50.0) * 0.40
        reasons.append(f"visual quality {visual:.0f}/100")
        if analysis.get("scenes", 1) > 1:
            reasons.append(f"{analysis['scenes']} visual scenes detected")

    transcript = analysis.get("transcript", {}) if analysis else {}
    if transcript.get("available") and transcript.get("segments"):
        score += 4
        reasons.append(f"{len(transcript['segments'])} speech segment(s) transcribed")

    active = analysis.get("audio", {}).get("active_ranges", []) if analysis else []
    if active:
        active_duration = sum(max(0.0, b - a) for a, b in active)
        silence = max(0.0, clip.duration - active_duration)
        if silence > 1.0:
            reasons.append(f"{silence:.1f}s removable audio dead time detected")
            score += min(8.0, silence / 3.0)

    if clip.duration < 12:
        score += 4
        reasons.append("compact source clip")
    elif clip.duration > 30:
        score -= 8
        reasons.append("long source clip; will be tightened")

    aspect = clip.width / clip.height if clip.height else 1
    if aspect < 0.8:
        score += 4
        reasons.append("vertical-friendly source")
    return round(max(0, min(score, 100)), 1), reasons


def _candidate_ranges(clip: Clip, settings: dict[str, Any]) -> list[list[float]]:
    analysis = clip.analysis or {}
    transcript = analysis.get("transcript", {}) if analysis else {}
    if settings["music_ducking"] and transcript.get("speech_ranges"):
        return transcript["speech_ranges"]
    active = analysis.get("audio", {}).get("active_ranges", []) if analysis else []
    return active


def best_window(clip: Clip, settings: dict[str, Any], max_len: float) -> tuple[float, float]:
    analysis = clip.analysis or {}
    hero = float(analysis.get("hero_time", 0.0))
    candidates = _candidate_ranges(clip, settings)
    if settings["remove_dead_time"] and candidates:
        candidates = sorted(candidates, key=lambda r: r[1] - r[0], reverse=True)
        for start, end in candidates[:7]:
            if end - start >= 0.6:
                center = (start + end) / 2.0
                start_at = max(0.0, min(center - max_len / 2, clip.duration - max_len))
                return round(start_at, 3), round(min(max_len, clip.duration - start_at), 3)
    start_at = max(0.0, min(hero - max_len / 2, max(0.0, clip.duration - max_len)))
    return round(start_at, 3), round(min(max_len, clip.duration - start_at), 3)


def _mapped_duck_ranges(item: dict[str, Any], clip: Clip, output_offset: float) -> list[list[float]]:
    transcript = (clip.analysis or {}).get("transcript", {})
    ranges = transcript.get("speech_ranges", []) if transcript else []
    if not ranges:
        return []
    source_start = float(item.get("source_start", 0))
    source_end = source_start + float(item.get("duration", 0))
    mapped = []
    for start, end in ranges:
        overlap_start = max(float(start), source_start)
        overlap_end = min(float(end), source_end)
        if overlap_end - overlap_start >= 0.12:
            mapped.append([
                round(output_offset + overlap_start - source_start, 3),
                round(output_offset + overlap_end - source_start, 3),
            ])
    return mapped


def build_plan(
    clips: list[Clip],
    prompt: str,
    duration: int,
    creative_direction: dict[str, Any] | None = None,
    naha_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = brief_settings(prompt, duration)
    creative_direction = creative_direction or {}
    naha_context = naha_context or {}
    scored = []
    for clip in clips:
        score, reasons = score_clip(clip, settings, creative_direction)
        scored.append({"clip": clip, "score": score, "reasons": reasons})
    scored.sort(key=lambda x: x["score"], reverse=True)

    max_per = min(4.0, max(0.6, float(settings["duration"])))
    remaining = float(settings["duration"])
    timeline, sequence_decisions = build_story_sequence(
        scored,
        creative_direction,
        max_duration=remaining,
        max_per_clip=max_per,
    )
    timeline = apply_pacing(timeline, float(settings["duration"]), settings["pace"])
    duck_ranges: list[list[float]] = []
    output_offset = 0.0

    # Resolve source windows and transcript metadata for the creative sequence.
    by_id = {item["clip"].id: item["clip"] for item in scored}
    for item in timeline:
        clip = by_id.get(item.get("clip_id"))
        if not clip:
            continue
        start, seg = best_window(clip, settings, min(float(item["duration"]), remaining))
        item["source_start"] = start
        item["source_end"] = round(start + seg, 3)
        item["duration"] = round(seg, 3)
        item["speech_ranges_source"] = (clip.analysis or {}).get("transcript", {}).get("speech_ranges", [])
        item["transcript_segments_source"] = (clip.analysis or {}).get("transcript", {}).get("segments", [])
        mapped_speech = []
        for speech_start, speech_end in (clip.analysis or {}).get("transcript", {}).get("speech_ranges", [])[:200]:
            overlap_start = max(float(speech_start), start)
            overlap_end = min(float(speech_end), start + seg)
            if overlap_end - overlap_start >= 0.12:
                mapped_speech.append([
                    round(output_offset + overlap_start - start, 3),
                    round(output_offset + overlap_end - start, 3),
                ])
        item["speech_ranges_output"] = mapped_speech
        duck_ranges.extend(_mapped_duck_ranges(item, clip, output_offset))
        remaining -= seg
        output_offset += seg

    if settings["logo_ending"] and remaining >= 1.0:
        logo_duration = min(2.2, remaining)
        timeline.append({
            "id": f"cut_{len(timeline) + 1}",
            "type": "logo",
            "enabled": True,
            "duration": round(logo_duration, 3),
            "label": "NAHALABS",
        })
        remaining -= logo_duration
        output_offset += logo_duration

    decisions = [
        {"step": 1, "action": "select", "rule": "Rank shots by creative relevance plus visual quality"},
        {"step": 2, "action": "trim", "rule": "Prefer speech/activity windows and remove dead time"},
        {"step": 3, "action": "pace", "rule": f"Use beat-aware {settings['pace']} pacing"},
    ]
    if settings["music_ducking"]:
        decisions.append({
            "step": 4, "action": "duck_music",
            "rule": "Lower music while transcribed speech is present when local transcript intelligence is available",
        })
    if settings["logo_ending"]:
        decisions.append({"step": 5, "action": "brand", "rule": "Finish with NahaLabs end card"})

    return {
        "version": "0.19",
        "prompt": prompt,
        "settings": settings,
        "creative_direction": creative_direction,
        "naha_context": naha_context,
        "shots_ranked": [
            {
                "id": x["clip"].id,
                "filename": x["clip"].filename,
                "score": x["score"],
                "reasons": x["reasons"],
                "analysis": x["clip"].analysis or {},
            }
            for x in scored
        ],
        "timeline": timeline,
        "unfilled_seconds": round(max(0, remaining), 3),
        "edit_decision_graph": decisions + [{"step": len(decisions) + 1, "action": "sequence", "rule": "Construct ordered creative story from intent-fit shots", "sequence": sequence_decisions}],
        "audio": {
            "dialogue_ducking_requested": settings["music_ducking"],
            "background_music": False,
            "duck_ranges": duck_ranges,
            "duck_mode": "transcript_ranges" if duck_ranges else "sidechain_fallback",
        },
        "branding": {"logo_id": None},
        "notes": [
            "v0.5 combines local media intelligence with a website-to-creative-brief intake layer.",
            "v0.19 adds NahaLabs lane/product/objective/format/authenticity context so creative intent can be reused across campaigns and production surfaces.",
            "v0.15 adds temporal per-shot semantic windows so intent scoring can identify the strongest evidence inside each detected scene.",
            "v0.17 adds approved stock assets as provenance-aware first-class footage; exact stock intent can fill an explicitly detected creative gap.",
            "Model adapters are optional; the CPU-only heuristic path remains usable without model downloads.",
            "Timeline entries are intentionally editable before rendering; derived captions/storyboard are rebuilt from the edited timeline.",
        ],
    }


def sanitize_plan(plan: dict[str, Any], allowed_clip_ids: set[str], target_duration: float | None = None) -> dict[str, Any]:
    clean = dict(plan)
    timeline = []
    total = 0.0
    limit = float(target_duration or plan.get("settings", {}).get("duration", 180))
    for raw in plan.get("timeline", []):
        item = dict(raw)
        if item.get("enabled", True) is False:
            continue
        if item.get("type") == "clip" and item.get("clip_id") not in allowed_clip_ids:
            continue
        try:
            duration = max(0.1, float(item.get("duration", 0)))
        except (TypeError, ValueError):
            continue
        if total + duration > limit:
            duration = max(0.0, limit - total)
        if duration < 0.1:
            break
        item["duration"] = round(duration, 3)
        if item.get("type") == "clip" and "source_start" in item:
            try:
                source_start = max(0.0, float(item["source_start"]))
                item["source_start"] = round(source_start, 3)
                item["source_end"] = round(source_start + duration, 3)
            except (TypeError, ValueError):
                pass
        timeline.append(item)
        total += duration
        if total >= limit - 0.001:
            break
    clean["timeline"] = timeline
    clean["unfilled_seconds"] = round(max(0.0, limit - total), 3)

    duck_ranges: list[list[float]] = []
    output_offset = 0.0
    for item in timeline:
        if item.get("type") == "clip":
            source_start = float(item.get("source_start", 0))
            duration = float(item.get("duration", 0))
            source_end = source_start + duration
            for start, end in item.get("speech_ranges_source", [])[:200]:
                overlap_start = max(float(start), source_start)
                overlap_end = min(float(end), source_end)
                if overlap_end - overlap_start >= 0.12:
                    duck_ranges.append([
                        round(output_offset + overlap_start - source_start, 3),
                        round(output_offset + overlap_end - source_start, 3),
                    ])
        output_offset += float(item.get("duration", 0))

    audio = dict(clean.get("audio", {}))
    audio["duck_ranges"] = duck_ranges
    audio["duck_mode"] = "transcript_ranges" if duck_ranges else "sidechain_fallback"
    clean["audio"] = audio
    return clean
