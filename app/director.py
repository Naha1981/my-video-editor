from dataclasses import dataclass, asdict
from typing import Any

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
    return {"duration": max(5, min(duration, 180)), "style": style, "pace": pace,
            "priority": "food" if food else "visual_story", "remove_dead_time": True,
            "music_ducking": wants_dialogue, "logo_ending": logo}

def score_clip(clip: Clip, settings: dict[str, Any]) -> tuple[float, list[str]]:
    name = clip.filename.lower()
    score = 50.0
    reasons: list[str] = []
    keyword_groups = {
        "food": ["food","dish","meal","burger","pizza","steak","dessert","plate","chef","kitchen","restaurant"],
        "people": ["person","people","customer","guest","waiter"],
        "hero": ["hero","close","closeup","final","best"],
    }
    if settings["priority"] == "food":
        hits = sum(1 for k in keyword_groups["food"] if k in name)
        score += min(22, hits * 7)
        if hits: reasons.append("food-related filename signal")
    if any(k in name for k in keyword_groups["hero"]):
        score += 10; reasons.append("hero/close-up filename signal")
    analysis = clip.analysis or {}
    if analysis:
        visual = float(analysis.get("visual_score", 50.0))
        score += (visual - 50.0) * 0.45
        reasons.append(f"visual quality {visual:.0f}/100")
        if analysis.get("scenes", 1) > 1: reasons.append(f"{analysis['scenes']} visual scenes detected")
    active = analysis.get("audio", {}).get("active_ranges", []) if analysis else []
    if active:
        active_duration = sum(max(0.0, b-a) for a,b in active)
        silence = max(0.0, clip.duration-active_duration)
        if silence > 1.0:
            reasons.append(f"{silence:.1f}s removable audio dead time detected")
            score += min(8.0, silence/3.0)
    if clip.duration < 12: score += 4; reasons.append("compact source clip")
    elif clip.duration > 30: score -= 8; reasons.append("long source clip; will be tightened")
    aspect = clip.width/clip.height if clip.height else 1
    if aspect < 0.8: score += 4; reasons.append("vertical-friendly source")
    return round(max(0,min(score,100)),1), reasons

def best_window(clip: Clip, settings: dict[str, Any], max_len: float) -> tuple[float,float]:
    analysis = clip.analysis or {}
    hero = float(analysis.get("hero_time",0.0))
    audio_ranges = analysis.get("audio",{}).get("active_ranges",[]) if analysis else []
    if settings["remove_dead_time"] and audio_ranges:
        candidates = sorted(audio_ranges,key=lambda r:r[1]-r[0],reverse=True)
        for start,end in candidates[:5]:
            if end-start >= 0.6:
                center=(start+end)/2.0
                start_at=max(0.0,min(center-max_len/2,clip.duration-max_len))
                return round(start_at,3),round(min(max_len,clip.duration-start_at),3)
    start_at=max(0.0,min(hero-max_len/2,max(0.0,clip.duration-max_len)))
    return round(start_at,3),round(min(max_len,clip.duration-start_at),3)

def build_plan(clips: list[Clip], prompt: str, duration: int) -> dict[str, Any]:
    settings=brief_settings(prompt,duration)
    scored=[]
    for clip in clips:
        score,reasons=score_clip(clip,settings)
        scored.append({"clip":clip,"score":score,"reasons":reasons})
    scored.sort(key=lambda x:x["score"],reverse=True)
    remaining=float(settings["duration"]); timeline=[]
    max_per=4.0 if settings["pace"]=="energetic" else 6.5
    for rank,item in enumerate(scored):
        if remaining<=0.25: break
        clip=item["clip"]
        cap=min(5.0,max_per+1.0) if rank==0 and settings["style"]=="premium" else max_per
        start,seg=best_window(clip,settings,min(cap,remaining))
        if seg<0.6: continue
        timeline.append({"type":"clip","clip_id":clip.id,"filename":clip.filename,
                         "source_start":start,"source_end":round(start+seg,3),"duration":round(seg,3),
                         "score":item["score"],"reasons":item["reasons"]})
        remaining-=seg
    if settings["logo_ending"] and remaining>=1.0:
        logo_duration=min(2.2,remaining)
        timeline.append({"type":"logo","duration":round(logo_duration,3),"label":"NAHALABS"})
        remaining-=logo_duration
    return {"version":"0.2","prompt":prompt,"settings":settings,
            "shots_ranked":[{"id":x["clip"].id,"filename":x["clip"].filename,"score":x["score"],
                             "reasons":x["reasons"],"analysis":x["clip"].analysis or {}} for x in scored],
            "timeline":timeline,"unfilled_seconds":round(max(0,remaining),3),
            "audio":{"dialogue_ducking_requested":settings["music_ducking"],"background_music":False},
            "notes":["v0.2 uses real local frame-quality, scene-change, and audio-activity signals.",
                     "Filename hints remain an explainable prior until a local vision-language model is connected."]}
