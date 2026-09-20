from app.captions import caption_emphasis, enrich_caption

def test_emphasis_is_restrained():
    assert caption_emphasis("Book today for a fresh special") == ["Book", "today", "fresh", "special"]

def test_normal_caption_has_no_emphasis():
    out=enrich_caption({"start":0,"end":1,"text":"The food is ready"})
    assert out["style"]=="normal"
    assert out["emphasis"]==[]
