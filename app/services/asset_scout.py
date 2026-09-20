from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..brief import fetch_brand
from ..integrations.jev import JevBrowserAgent, JevBrowserError
from ..integrations.nahallm import NahaLLMClient, NahaLLMError
from .mission_compiler import compile_asset_mission


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        raise ValueError("Browser interpretation did not return an object")
    return value


def _fallback_observations(site: dict[str, Any]) -> list[dict[str, Any]]:
    meta = site.get("meta") or {}
    observations: list[dict[str, Any]] = []
    for field, value in (
        ("business_name", site.get("title") or meta.get("og:title")),
        ("hero_image", meta.get("og:image")),
        ("website_description", meta.get("description") or meta.get("og:description")),
    ):
        if value:
            observations.append({
                "field": field,
                "value": str(value),
                "source_url": site.get("url"),
                "observed_at": _now(),
                "verification": "observed_by_deterministic_website_intake",
            })
    return observations


def interpret_result(result: dict[str, Any], llm: NahaLLMClient) -> dict[str, Any]:
    system = (
        "You are the NahaLabs evidence interpreter. Convert browser observations into structured "
        "facts without inventing anything. Return ONLY JSON with keys observations and assets. "
        "Each observation must contain field, value, source_url, verification. Each asset must contain "
        "kind, url, purpose, source_url, verification. Never claim a licence is approved."
    )
    content, trace = llm.text(
        system,
        json.dumps({
            "source_url": result.get("source_url"),
            "final_url": result.get("final_url"),
            "browser_observations": result.get("observations") or [],
            "browser_assets": result.get("assets") or [],
        }, ensure_ascii=False),
        model="fast",
        max_tokens=1800,
    )
    interpreted = _json_object(content)
    interpreted["llm_trace"] = trace
    return interpreted


def scout_website_assets(
    url: str,
    prompt: str = "",
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    site = fetch_brand(url)
    llm = NahaLLMClient()
    worker = JevBrowserAgent()
    mission, compilation = compile_asset_mission(url, prompt, metadata, llm=llm)

    base: dict[str, Any] = {
        "mission_id": mission.mission_id,
        "source_url": mission.source_url,
        "completed": False,
        "observations": _fallback_observations(site),
        "assets": [],
        "trace": [],
        "errors": [],
        "final_url": site.get("url"),
        "observed_at": _now(),
        "mission": {
            "goal": mission.goal,
            "requirements": mission.requirements,
            "metadata": mission.metadata,
        },
        "compiler": compilation,
        "browser": worker.start(),
    }

    if not worker.enabled:
        base["status"] = "browser_disabled"
        base["errors"].append("Jev is disabled; deterministic website intake remains active.")
        return base

    try:
        browser_result = worker.run_mission(mission).as_dict()
        base.update({
            "completed": browser_result["completed"],
            "observations": browser_result["observations"] or base["observations"],
            "assets": browser_result["assets"],
            "trace": browser_result["trace"],
            "errors": browser_result["errors"],
            "final_url": browser_result["final_url"] or base["final_url"],
            "observed_at": browser_result["observed_at"] or base["observed_at"],
            "status": "completed" if browser_result["completed"] else "partial",
        })
        if llm.enabled and base["observations"]:
            try:
                interpreted = interpret_result(base, llm)
                base["observations"] = interpreted.get("observations") or base["observations"]
                base["assets"] = interpreted.get("assets") or base["assets"]
                base["interpretation"] = {
                    "source": "NahaLLM",
                    "trace": interpreted.get("llm_trace"),
                }
            except (NahaLLMError, ValueError, json.JSONDecodeError, TypeError) as exc:
                base["errors"].append(f"LLM interpretation fallback: {type(exc).__name__}: {exc}")
    except JevBrowserError as exc:
        base["status"] = "browser_failed"
        base["errors"].append(str(exc))
    except Exception as exc:
        base["status"] = "failed"
        base["errors"].append(f"{type(exc).__name__}: {exc}")

    return base
