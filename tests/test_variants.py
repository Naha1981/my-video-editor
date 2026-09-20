from __future__ import annotations

from app.variants import render_variants


def test_render_variants_rejects_missing_source(tmp_path):
    out = render_variants(tmp_path / "missing.mp4", tmp_path / "out", ["9:16"])
    assert out["status"] == "failed"


def test_render_variants_ignores_unknown_formats(tmp_path, monkeypatch):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"x")
    monkeypatch.setattr("app.variants.focal_point", lambda path, sample_time=0.0: {"x": 0.5, "y": 0.5, "confidence": 0.1})
    monkeypatch.setattr("app.variants.subprocess.run", lambda *args, **kwargs: type("P", (), {"returncode": 1, "stderr": "expected fixture"})())
    out = render_variants(source, tmp_path / "out", ["9:16", "bogus"])
    assert len(out["results"]) == 1
    assert out["results"][0]["aspect"] == "9:16"


def test_crop_filter_contains_focal_bias():
    from app.focal import crop_filter
    out = crop_filter(1080, 1920, {"x": 0.72, "y": 0.38})
    assert "0.7200" in out
    assert "0.3800" in out


def test_focal_point_has_safe_center_fallback(tmp_path, monkeypatch):
    from app.focal import focal_point
    monkeypatch.setattr("app.focal.subprocess.run", lambda *args, **kwargs: type("P", (), {"returncode": 1, "stdout": b""})())
    out = focal_point(tmp_path / "missing.mp4")
    assert out["x"] == 0.5
    assert out["y"] == 0.5


def test_render_variants_accepts_timeline_for_per_shot_reframing(tmp_path, monkeypatch):
    import app.variants as variants
    source = tmp_path / "source.mp4"
    source.write_bytes(b"x")
    calls = []
    monkeypatch.setattr(variants, "focal_point", lambda path, sample_time=0.0: calls.append(sample_time) or {"x": 0.5, "y": 0.5, "confidence": 0.1})
    monkeypatch.setattr(variants.subprocess, "run", lambda *args, **kwargs: type("P", (), {"returncode": 1, "stderr": "expected fixture"})())
    out = variants.render_variants(
        source, tmp_path / "out", ["9:16"],
        timeline=[{"type": "clip", "duration": 2}, {"type": "clip", "duration": 3}],
    )
    assert out["reframing"] == "per-shot"
    assert calls == [0.05, 2.05]


def test_caption_safe_zones_differ_by_aspect():
    from app.variants import caption_safe_zone
    assert caption_safe_zone("9:16")["margin_v"] > caption_safe_zone("16:9")["margin_v"]
    assert caption_safe_zone("1:1")["font_size"] != caption_safe_zone("16:9")["font_size"]
