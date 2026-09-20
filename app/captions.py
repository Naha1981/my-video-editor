from __future__ import annotations

from typing import Any
import re

def split_caption_text(text: str, max_words: int = 6, max_chars: int = 34) -> list[str]:
    words = re.findall(r"\S+", str(text or "").strip())
    if not words:
        return []
    chunks=[]; current=[]
    for word in words:
        candidate=" ".join(current+[word])
        if current and (len(current)>=max_words or len(candidate)>max_chars):
            chunks.append(" ".join(current)); current=[word]
        else:
            current.append(word)
    if current: chunks.append(" ".join(current))
    return chunks

def segment_caption(segment: dict[str, Any], max_words: int = 6, max_chars: int = 34) -> list[dict[str, Any]]:
    start=float(segment.get("start",0) or 0); end=float(segment.get("end",start) or start)
    if end<=start: return []
    chunks=split_caption_text(segment.get("text",""),max_words,max_chars)
    if not chunks: return []
    span=end-start
    total=max(1,len(chunks))
    out=[]
    for i,text in enumerate(chunks):
        a=start+span*i/total; b=start+span*(i+1)/total
        out.append({"start":round(a,3),"end":round(b,3),"text":text})
    return out

def build_caption_track(segments: list[dict[str,Any]] | None) -> list[dict[str,Any]]:
    return [cap for seg in (segments or []) for cap in segment_caption(seg)]


EMPHASIS_WORDS = {
    "new", "now", "free", "save", "limited", "today", "book", "order",
    "fresh", "premium", "exclusive", "special", "discover", "more",
}


def caption_emphasis(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9À-ÿ']+", str(text or ""))
    return [word for word in words if word.lower() in EMPHASIS_WORDS]


def caption_style(text: str, emphasis: list[str] | None = None) -> str:
    """Choose restrained visual hierarchy from message content, not animation noise."""
    words = re.findall(r"\\S+", str(text or "").strip())
    emphasized = emphasis if emphasis is not None else caption_emphasis(text)
    if len(words) <= 4 and emphasized:
        return "hero"
    if emphasized:
        return "emphasis"
    return "normal"


def enrich_caption(cap: dict[str, Any]) -> dict[str, Any]:
    out = dict(cap)
    emphasis = caption_emphasis(out.get("text", ""))
    out["emphasis"] = emphasis
    out["style"] = caption_style(out.get("text", ""), emphasis)
    return out


def caption_rhythm(caption: dict[str, Any], *, beat_times: list[float] | None = None, creative_intent: str | None = None) -> dict[str, Any]:
    """Attach timing/rhythm guidance without changing the spoken words."""
    out = dict(caption)
    start=float(out.get("start",0) or 0); end=float(out.get("end",start) or start)
    duration=max(0.0,end-start)
    beats=sorted(float(x) for x in (beat_times or []) if float(x)>=0)
    nearest=min((abs(b-start), b) for b in beats) if beats else (999.0,None)
    style=str(out.get("style","normal"))
    intent=str(creative_intent or "")
    # Commercial hooks and hero statements deserve a little breathing room.
    if style=="hero" or intent in {"hero_food","cta"}:
        rhythm="accent"
    elif nearest[0] <= 0.16:
        rhythm="beat"
    elif duration < 0.75:
        rhythm="quick"
    else:
        rhythm="steady"
    out["rhythm"]=rhythm
    out["beat_distance"]=round(float(nearest[0]),3) if nearest[1] is not None else None
    return out
