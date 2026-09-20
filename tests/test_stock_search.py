from app.stock_search import build_stock_manifest

def test_stock_manifest_creates_provider_search_jobs_for_missing_gaps():
    out = build_stock_manifest([{
        "beat": "cta",
        "intent": "cta",
        "priority": "required",
        "status": "missing",
        "need": "restaurant exterior storefront",
        "search_hint": "restaurant exterior storefront booking order",
    }])
    assert out["status"] == "search_required"
    assert out["job_count"] == 1
    assert len(out["jobs"][0]["providers"]) == 3
    assert "restaurant+exterior" in out["jobs"][0]["providers"][0]["url"]

def test_stock_manifest_does_not_search_when_no_gaps():
    out = build_stock_manifest([])
    assert out["status"] == "no_stock_needed"
    assert out["jobs"] == []
