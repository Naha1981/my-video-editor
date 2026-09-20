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
