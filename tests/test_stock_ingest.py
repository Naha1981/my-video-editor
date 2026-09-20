from pathlib import Path

from app.stock_ingest import enrich_analysis_with_stock, read_stock_asset, register_stock_asset


def test_stock_asset_registration_persists_provenance(tmp_path: Path):
    media = tmp_path / "restaurant_exterior.mp4"
    media.write_bytes(b"stub")
    data = register_stock_asset(
        media,
        beat="cta",
        intent="cta",
        provider="pexels",
        source_url="https://www.pexels.com/video/example",
        license_name="Pexels",
        attribution="Creator Name / Pexels",
        approved=True,
    )
    assert data["provenance_status"] == "approved"
    stored = read_stock_asset(media)
    assert stored["provider"] == "pexels"
    assert stored["approved"] is True


def test_stock_asset_enriches_analysis_without_overwriting_semantics(tmp_path: Path):
    media = tmp_path / "hero.mp4"
    media.write_bytes(b"stub")
    register_stock_asset(
        media,
        beat="hook",
        intent="hero_food",
        provider="pexels",
        source_url="https://www.pexels.com/video/example",
        approved=True,
    )
    analysis = {"semantic": {"labels": {"food": 0.2}}}
    enriched = enrich_analysis_with_stock(analysis, media)
    assert enriched["semantic"]["labels"]["food"] == 0.2
    assert enriched["stock"]["intent"] == "hero_food"


def test_approved_stock_requires_provenance(tmp_path: Path):
    media = tmp_path / "hero.mp4"
    media.write_bytes(b"stub")
    try:
        register_stock_asset(media, beat="hook", intent="hero_food", approved=True)
        assert False, "expected provenance validation"
    except ValueError as exc:
        assert "provenance" in str(exc)
