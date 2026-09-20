import app.services.asset_scout as scout


def test_asset_scout_api_path_can_remain_disabled(monkeypatch):
    monkeypatch.delenv("NAHALLM_ENABLED", raising=False)
    monkeypatch.delenv("JEV_ENABLED", raising=False)
    from app.main import AssetScoutRequest
    assert AssetScoutRequest(url="https://example.com").task == ""


def test_fallback_observations_preserve_source():
    data = {
        "url": "https://example.com",
        "title": "Example",
        "meta": {"og:image": "https://example.com/hero.jpg"},
    }
    observations = scout._fallback_observations(data)
    assert any(item["field"] == "hero_image" for item in observations)
    assert all(item["source_url"] == "https://example.com" for item in observations)
