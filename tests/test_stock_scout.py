from app.services.stock_scout import stock_missions_from_gaps


def test_stock_missions_only_use_missing_gaps():
    jobs = stock_missions_from_gaps([
        {"status": "covered", "beat": "hook", "intent": "hero_food", "search_hint": "food"},
        {"status": "missing", "beat": "cta", "intent": "cta", "search_hint": "restaurant exterior"},
    ])
    assert jobs
    assert {x["provider"] for x in jobs} == {"pexels", "pixabay", "mixkit"}
    assert all(x["intent"] == "cta" for x in jobs)
