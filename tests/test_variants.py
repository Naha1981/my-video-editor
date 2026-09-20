from __future__ import annotations

from pathlib import Path
from app.variants import render_variants

def test_render_variants_rejects_missing_source(tmp_path):
    out = render_variants(tmp_path / "missing.mp4", tmp_path / "out", ["9:16"])
    assert out["status"] == "failed"

def test_render_variants_ignores_unknown_formats(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"x")
    out = render_variants(source, tmp_path / "out", ["9:16", "bogus"])
    assert len(out["results"]) == 1
    assert out["results"][0]["aspect"] == "9:16"


def test_crop_filter_contains_focal_bias():
    from app.focal import crop_filter
    out = crop_filter(1080, 1920, {"x": 0.72, "y": 0.38})
    assert "0.7200" in out
    assert "0.3800" in out
