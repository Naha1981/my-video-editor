from pathlib import Path


def test_stock_approval_round_trip(tmp_path, monkeypatch):
    import app.main as main
    from app.stock_ingest import register_stock_asset, read_stock_asset

    asset = tmp_path / "abc123.mp4"
    asset.write_bytes(b"not-real-video")
    register_stock_asset(asset, beat="cta", intent="cta", provider="Pexels", source_url="https://pexels.com/v")

    monkeypatch.setattr(main, "_find_media", lambda _asset_id: asset)
    result = main.approve_asset("abc123")
    assert result["approved"] is True
    assert result["provenance_status"] == "approved_by_operator"
    assert read_stock_asset(asset)["approved"] is True
