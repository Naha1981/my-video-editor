from __future__ import annotations

import json
import uuid
from typing import Any

from ..integrations.nahallm import NahaLLMClient, NahaLLMError
from ..integrations.jev import JevMission

DEFAULT_REQUIREMENTS = [
    "business_name",
    "location",
    "phone",
    "whatsapp",
    "primary_cta",
    "menu_or_services",
    "booking_or_ordering",
    "brand_logo",
    "hero_images",
    "useful_brand_pages",
]


def deterministic_asset_mission(url: str, prompt: str = "", metadata: dict[str, Any] | None = None) -> JevMission:
    metadata = metadata or {}
    task = prompt.strip() or (
        "Inspect the website and collect only observable information and public assets useful "
        "for a customer-facing video. Do not purchase, submit forms, or authenticate."
    )
    return JevMission(
        mission_id="jev_" + uuid.uuid4().hex[:16],
        source_url=url,
        goal=task,
        requirements=list(DEFAULT_REQUIREMENTS),
        metadata=metadata,
    )


def _json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fence = chr(96) * 3
    if candidate.startswith(fence):
        candidate = candidate.replace(fence + "json", "", 1).replace(fence, "").strip()
    start, end = candidate.find("{"), candidate.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found")
    value = json.loads(candidate[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Mission compiler did not return an object")
    return value


def compile_asset_mission(
    url: str,
    prompt: str = "",
    metadata: dict[str, Any] | None = None,
    llm: NahaLLMClient | None = None,
) -> tuple[JevMission, dict[str, Any]]:
    fallback = deterministic_asset_mission(url, prompt, metadata)
    llm = llm or NahaLLMClient()
    if not llm.enabled:
        return fallback, {"source": "deterministic_fallback", "llm": False}

    system = (
        "You compile browser missions for NahaLabs. Return ONLY valid JSON with exactly these keys: "
        "goal (string), requirements (array of short strings), forbidden_actions (array of short strings). "
        "The browser worker collects observable website evidence and public asset links. "
        "It must not purchase, submit payments, change account settings, reveal secrets, authenticate, "
        "or invent missing facts. Keep requirements to at most 16 items."
    )
    user = json.dumps({
        "url": url,
        "operator_request": prompt,
        "metadata": metadata or {},
        "default_requirements": DEFAULT_REQUIREMENTS,
    }, ensure_ascii=False)

    try:
        content, trace = llm.text(system, user, model="fast", max_tokens=1000)
        obj = _json_object(content)
        goal = str(obj.get("goal") or fallback.goal).strip()
        requirements = [
            str(item).strip()
            for item in (obj.get("requirements") or DEFAULT_REQUIREMENTS)
            if str(item).strip()
        ][:16]
        forbidden = [
            str(item).strip()
            for item in (obj.get("forbidden_actions") or [])
            if str(item).strip()
        ][:12]
        mission = JevMission(
            mission_id=fallback.mission_id,
            source_url=url,
            goal=goal,
            requirements=requirements or list(DEFAULT_REQUIREMENTS),
            metadata={
                **(metadata or {}),
                "forbidden_actions": forbidden,
                "compiler": "NahaLLM",
            },
        )
        return mission, {"source": "NahaLLM", "llm": True, "trace": trace}
    except (NahaLLMError, ValueError, json.JSONDecodeError, TypeError) as exc:
        return fallback, {
            "source": "deterministic_fallback",
            "llm": True,
            "fallback_reason": f"{type(exc).__name__}: {exc}",
        }
