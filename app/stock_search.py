from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus


PROVIDERS = {
    "pexels": "https://www.pexels.com/search/videos/{query}/",
    "pixabay": "https://pixabay.com/videos/search/{query}/",
    "mixkit": "https://mixkit.co/free-stock-video/{query}/",
}


def build_stock_queries(gaps: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Turn Director footage gaps into provider-ready stock search jobs."""
    jobs = []
    for gap in gaps or []:
        if gap.get("status") != "missing":
            continue
        query = str(gap.get("search_hint") or gap.get("need") or "").strip()
        if not query:
            continue
        jobs.append({
            "beat": gap.get("beat"),
            "intent": gap.get("intent"),
            "priority": gap.get("priority", "supporting"),
            "query": query,
            "providers": [
                {"name": name, "url": template.format(query=quote_plus(query))}
                for name, template in PROVIDERS.items()
            ],
        })
    return jobs


def build_stock_manifest(gaps: list[dict[str, Any]] | None) -> dict[str, Any]:
    jobs = build_stock_queries(gaps)
    return {
        "status": "search_required" if jobs else "no_stock_needed",
        "job_count": len(jobs),
        "jobs": jobs,
        "notes": [
            "Stock is only proposed for Director-detected missing footage.",
            "The Director never invents footage or silently substitutes stock.",
            "Provider URLs are search destinations; downloading remains an explicit user/provider step until an API key is configured.",
        ],
    }
