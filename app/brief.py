from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import re


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.title=[]; self._in_title=False; self.meta={}
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag.lower()=="title": self._in_title=True
        if tag.lower()=="meta":
            key=(d.get("property") or d.get("name") or "").lower()
            if key in {"description","og:title","og:description","og:image","twitter:title","twitter:description"}:
                self.meta[key]=d.get("content","").strip()
    def handle_endtag(self, tag):
        if tag.lower()=="title": self._in_title=False
    def handle_data(self, data):
        if self._in_title: self.title.append(data.strip())


def fetch_brand(url: str, timeout: int = 12) -> dict:
    parsed=urlparse(url if "://" in url else "https://"+url)
    if parsed.scheme not in {"http","https"} or not parsed.netloc:
        raise ValueError("Enter a valid http(s) website URL")
    target=parsed.geturl()
    req=Request(target,headers={"User-Agent":"NahaVideo/0.5 (+local creative intake)"})
    with urlopen(req,timeout=timeout) as r:
        raw=r.read(750_000).decode("utf-8","ignore")
    p=_MetaParser(); p.feed(raw)
    title=" ".join(x for x in p.title if x).strip()
    text=re.sub(r"\\s+"," ",re.sub(r"<[^>]+>"," ",raw))[:12000]
    return {"url":target,"domain":parsed.netloc,"title":title,"meta":p.meta,"text":text}


def compile_creative_brief(site: dict, user_prompt: str = "") -> dict:
    meta=site.get("meta",{}); title=site.get("title") or meta.get("og:title") or site.get("domain","")
    description=meta.get("description") or meta.get("og:description") or ""
    corpus=(title+" "+description+" "+site.get("text","")).lower()
    vertical="restaurant" if any(x in corpus for x in ["restaurant","menu","food","chef","dining","delivery"]) else "business"
    offer=description[:220] if description else title
    audience="local customers" if vertical=="restaurant" else "prospective customers"
    cta="Visit us / enquire today" if vertical=="restaurant" else "Learn more / enquire today"
    if any(x in corpus for x in ["book","reservation","table"]): cta="Book your table"
    if any(x in corpus for x in ["shop","store","buy","order"]): cta="Shop / order now"
    tone="premium, confident, authentic" if any(x in corpus for x in ["luxury","premium","exclusive","fine dining"]) else "modern, clear, human"
    visual=["hero product/service","real people","location/environment","detail shots","brand/CTA"]
    return {"business_name":title[:100],"website":site.get("url",""),"category":vertical,"offer":offer,"audience":audience,"tone":tone,"cta":cta,"visual_keywords":visual,"source":"website metadata + visible text","user_prompt":user_prompt.strip()}
