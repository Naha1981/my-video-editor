from app.variants import _write_ass

def test_ass_caption_renders_only_local_shot_window(tmp_path):
    path=tmp_path/"caption.ass"
    out=_write_ass(path,[{"start":2,"end":3,"text":"Book today","emphasis":["Book"]},{"start":5,"end":6,"text":"Fresh food","emphasis":["Fresh"]}],{"alignment":2,"margin_v":220,"font_size":20},offset=2,duration=2)
    assert out==path
    text=path.read_text(encoding="utf-8")
    assert "Dialogue: 0,0:00:00.00,0:00:01.00" in text
    assert "Book" in text and "today" in text
    assert "Fresh food" not in text
    assert r"\b1\fs22" in text


def test_ass_caption_uses_rhythm_aware_fade(tmp_path):
    path=tmp_path/"rhythm.ass"
    out=_write_ass(path,[{"start":1,"end":2,"text":"Book today","style":"hero","rhythm":"accent"}],{"alignment":2,"margin_v":220,"font_size":20})
    assert out==path
    text=path.read_text(encoding="utf-8")
    assert r"\fad(180,180)" in text
