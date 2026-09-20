from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from ..integrations.jev import JevBrowserAgent, JevBrowserError
from ..integrations.jev.models import JevMission
from .asset_fetcher import collect_public_assets


PROVIDERS = {
    "pexels": "https://www.pexels.com/search/videos/{query}/",
    "pixabay": "https://pixabay.com/videos/search/{query}/",
    "mixkit": "https://mixkit.co/free-stock-video/{query}/",
}


def stock_missions_from_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    jobs = []
    for gap in gaps or []:
        if gap.get("status") != "missing":
            continue
        query = str(gap.get("search_hint") or gap.get("need") or "").strip()
        if not query:
            continue
        for provider, template in PROVIDERS.items():
            jobs.append({
                "provider": provider,
                "url": template.format(query=quote_plus(query)),
                "query": query,
                "intent": gap.get("intent"),
                "beat": gap.get("beat"),
                "priority": gap.get("priority", "supporting"),
            })
    return jobs


def scout_missing_stock(gaps: list[dict[str, Any]], max_missions: int = 6) -> dict[str, Any]:
    worker = JevBrowserAgent()
    if not worker.enabled:
        return {"status": "disabled", "missions": [], "candidates": [], "collected_assets": []}

    missions = stock_missions_from_gaps(gaps)[:max(1, max_missions)]
    results = []
    all_candidates = []
    collected = []

    for job in missions:
        mission = JevMission(
            mission_id=f"stock_{job['provider']}_{job['beat']}",
            source_url=job["url"],
            goal=(
                f"Find up to 3 useful free stock video candidates for '{job['query']}'. "
                "Prefer real, downloadable video assets or candidate pages. Do not purchase, "
                "sign in, submit forms, or select paid-only assets."
            ),
            requirements=[
                "candidate stock video pages",
                "direct visible video media when publicly loaded",
                "candidate title or nearby descriptive text",
            ],
            metadata={
                "provider": job["provider"],
                "intent": job["intent"],
                "beat": job["beat"],
                "priority": job["priority"],
            },
        )
        try:
            result = worker.run_mission(mission).as_dict()
            for asset in result.get("assets") or []:
                enriched = {
                    **asset,
                    "provider": job["provider"],
                    "intent": job["intent"],
                    "beat": job["beat"],
                    "priority": job["priority"],
                }
                all_candidates.append(enriched)
            results.append({
                "provider": job["provider"],
                "query": job["query"],
                "status": "completed" if result.get("completed") else "partial",
                "mission_id": result.get("mission_id"),
                "errors": result.get("errors", []),
            })
            provider_page = job["url"]
            media_candidates = [
                x for x in all_candidates[-120:]
                if x.get("kind") in {"video", "direct_media"}
            ]
            if media_candidates:
                collected.extend(collect_public_assets(media_candidates, source_url=provider_page, max_assets=4))
        except JevBrowserError as exc:
            results.append({
                "provider": job["provider"],
                "query": job["query"],
                "status": "failed",
                "errors": [str(exc)],
            })

    return {
        "status": "completed" if results else "no_missions",
        "missions": results,
        "candidates": all_candidates[:120],
        "collected_assets": collected,
    }
