from app.services.asset_fetcher import _allowed


def test_asset_allowed_on_source_domain(monkeypatch):
    monkeypatch.setattr(
        "app.services.asset_fetcher._resolve_public",
        lambda _host: {"93.184.216.34"},
    )
    assert _allowed("https://www.example.com/hero.jpg", "https://example.com/menu")


def test_asset_other_domain_requires_explicit_allowlist(monkeypatch):
    monkeypatch.setattr(
        "app.services.asset_fetcher._resolve_public",
        lambda _host: {"93.184.216.34"},
    )
    monkeypatch.delenv("NAHAVIDEO_ASSET_ALLOWED_DOMAINS", raising=False)
    assert not _allowed("https://cdn.example.net/hero.jpg", "https://example.com/menu")


def test_asset_configured_cdn_domain_allowed(monkeypatch):
    monkeypatch.setattr(
        "app.services.asset_fetcher._resolve_public",
        lambda _host: {"93.184.216.34"},
    )
    monkeypatch.setenv("NAHAVIDEO_ASSET_ALLOWED_DOMAINS", "cdn.example.net")
    assert _allowed("https://cdn.example.net/hero.jpg", "https://example.com/menu")
