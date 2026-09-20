from app.captions import caption_style, enrich_caption

def test_short_commercial_statement_gets_hero_style():
    assert caption_style("Book today", ["Book", "today"]) == "hero"

def test_long_emphasis_stays_subtle():
    assert caption_style("Book your table today for fresh food", ["Book", "today", "fresh"]) == "emphasis"

def test_plain_dialogue_stays_normal():
    assert enrich_caption({"text": "We open at six"})["style"] == "normal"
