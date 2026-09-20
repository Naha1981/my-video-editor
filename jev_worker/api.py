from __future__ import annotations

import ipaddress
import os
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="NahaLabs Jev Browser Worker", version="0.1.0")


class MissionRequest(BaseModel):
    mission_id: str = Field(min_length=1, max_length=80)
    url: str
    goal: str = Field(min_length=1, max_length=4000)
    requirements: list[str] = Field(default_factory=list, max_length=16)
    metadata: dict = Field(default_factory=dict)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_auth(authorization: str | None) -> None:
    expected = os.getenv("JEV_WORKER_API_KEY", "").strip()
    if not expected:
        raise HTTPException(503, "JEV_WORKER_API_KEY is not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(401, "Invalid Jev worker API key")


def _validate_url(url: str) -> str:
    value = url.strip()
    parsed = urlparse(value if "://" in value else "https://" + value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Jev target must be a valid http(s) URL")
    host = parsed.hostname.lower().rstrip(".")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise HTTPException(400, f"Target hostname could not be resolved: {host}") from exc
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise HTTPException(400, "Jev refuses private, local, link-local, multicast or reserved targets")
    allowlist = [
        item.strip().lower().lstrip(".")
        for item in os.getenv("JEV_ALLOWED_DOMAINS", "").split(",")
        if item.strip()
    ]
    if allowlist and not any(host == rule or host.endswith("." + rule) for rule in allowlist):
        raise HTTPException(403, "Target domain is not in JEV_ALLOWED_DOMAINS")
    return parsed.geturl()


EXTRACT_PUBLIC_ASSETS = """
(() => {
  const clean = (value) => (value || '').trim();
  const visible = (e) => {
    if (!e) return false;
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
  };
  const imageUrls = [...document.images]
    .filter(visible)
    .map((e) => e.currentSrc || e.src || '')
    .filter((u) => /^https?:/i.test(u))
    .slice(0, 80);
  const videoUrls = [...document.querySelectorAll('video, video source, source[src]')]
    .filter(visible)
    .map((e) => e.currentSrc || e.src || '')
    .filter((u) => /^https?:/i.test(u))
    .slice(0, 80);
  const mediaLinks = [...document.querySelectorAll('a[href]')]
    .filter(visible)
    .map((e) => ({text: clean(e.innerText).slice(0, 240), url: e.href}))
    .filter((x) => /^https?:/i.test(x.url))
    .filter((x) => /\.(mp4|webm|mov)(?:[?#]|$)/i.test(x.url))
    .slice(0, 80);
  const links = [...document.querySelectorAll('a[href]')]
    .filter(visible)
    .map((e) => ({text: clean(e.innerText).slice(0, 240), url: e.href}))
    .filter((x) => /^https?:/i.test(x.url))
    .slice(0, 120);
  return {
    image_urls: [...new Set(imageUrls)],
    video_urls: [...new Set([...videoUrls, ...mediaLinks.map(x => x.url)])],
    links
  };
})()
"""


def _sanitize_trace(history: list[dict]) -> list[dict]:
    out = []
    for item in history[-80:]:
        out.append({
            "step": item.get("step"),
            "action": item.get("action"),
            "kind": item.get("kind"),
            "url": item.get("url"),
            "page_changed": item.get("page_changed"),
            "elapsed_ms": item.get("elapsed_ms"),
            "executed_ms": item.get("executed_ms"),
        })
    return out


def _run_agent(req: MissionRequest, target: str) -> dict:
    from jev_ultrafast import Agent

    timeout_seconds = max(15, float(os.getenv("JEV_MISSION_TIMEOUT_SECONDS", "180")))
    max_steps = max(1, int(os.getenv("JEV_MAX_STEPS", "40")))

    started = time.monotonic()
    final_state = None
    errors: list[str] = []

    with Agent(target, req.goal, screenshots=False) as agent:
        for _ in range(max_steps):
            if time.monotonic() - started > timeout_seconds:
                errors.append("mission timeout")
                break
            try:
                final_state = agent.command("tick")
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                break
            if final_state.get("status") in {"done", "blocked"}:
                break

        if final_state is None:
            final_state = agent.snapshot()

        try:
            public_assets = agent.browser.evaluate(EXTRACT_PUBLIC_ASSETS) or {"image_urls": [], "video_urls": [], "links": []}
        except Exception as exc:
            public_assets = {"image_urls": [], "video_urls": [], "links": []}
            errors.append(f"asset extraction: {type(exc).__name__}: {exc}")

        observations = [
            {
                "field": "page_title",
                "value": final_state.get("page", {}).get("title"),
                "source_url": final_state.get("page", {}).get("url") or target,
                "observed_at": _utc(),
                "verification": "browser_observed",
            },
            {
                "field": "visible_page_text",
                "value": (final_state.get("page", {}).get("text") or "")[:12000],
                "source_url": final_state.get("page", {}).get("url") or target,
                "observed_at": _utc(),
                "verification": "browser_observed",
            },
        ]

    assets = [
        {
            "kind": "video",
            "url": url,
            "purpose": "public_visible_video",
            "source_url": final_state.get("page", {}).get("url") or target,
            "verification": "browser_observed_public_media",
        }
        for url in public_assets.get("video_urls", [])[:40]
    ] + [
        {
            "kind": "image",
            "url": url,
            "purpose": "public_visible_image",
            "source_url": final_state.get("page", {}).get("url") or target,
            "verification": "browser_observed_public_link",
        }
        for url in public_assets.get("image_urls", [])[:80]
    ]
    assets.extend(
        {
            "kind": "page_link",
            "url": item["url"],
            "purpose": "public_visible_link",
            "label": item.get("text", ""),
            "source_url": final_state.get("page", {}).get("url") or target,
            "verification": "browser_observed_public_link",
        }
        for item in public_assets.get("links", [])[:120]
    )

    return {
        "mission_id": req.mission_id,
        "source_url": target,
        "completed": final_state.get("status") == "done",
        "observations": observations,
        "assets": assets,
        "trace": _sanitize_trace(final_state.get("history", [])),
        "errors": errors,
        "final_url": final_state.get("page", {}).get("url") or target,
        "observed_at": _utc(),
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "nahalabs-jev-worker",
        "configured": bool(os.getenv("JEV_WORKER_API_KEY")),
    }


@app.post("/run")
def run(req: MissionRequest, authorization: str | None = Header(default=None)):
    _check_auth(authorization)
    target = _validate_url(req.url)
    result = _run_agent(req, target)
    result["worker_run_id"] = "run_" + uuid4().hex[:12]
    return result
