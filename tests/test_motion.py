from pathlib import Path

from app.motion import render_brand_card


def test_motion_engine_receives_nahalabs_context(tmp_path):
    seen = {}

    def engine(**kwargs):
        seen.update(kwargs)
        out = tmp_path / "brand.mp4"
        out.write_bytes(b"ok")
        return out

    result = render_brand_card(tmp_path, 2.0, context={"style": "premium"}, engine=engine)

    assert result.exists()
    assert seen["context"]["brand"] == "NahaLabs"
    assert seen["context"]["product"] == "NahaVideo AI Director"
    assert seen["context"]["format"]["width"] == 1080
    assert seen["context"]["style"] == "premium"


def test_motion_engine_missing_output_fails(tmp_path):
    def engine(**kwargs):
        return tmp_path / "missing.mp4"

    try:
        render_brand_card(tmp_path, 2.0, engine=engine)
        assert False, "expected missing-output error"
    except RuntimeError as exc:
        assert "missing output" in str(exc)
