from app.captions import caption_rhythm

def test_hero_caption_gets_accent_rhythm():
    out=caption_rhythm({"start":1,"end":2,"text":"Book today","style":"hero"},creative_intent="cta")
    assert out["rhythm"]=="accent"

def test_caption_near_music_beat_gets_beat_rhythm():
    out=caption_rhythm({"start":1.02,"end":1.8,"text":"Dinner is ready","style":"normal"},beat_times=[1.0])
    assert out["rhythm"]=="beat"

def test_short_caption_gets_quick_rhythm():
    out=caption_rhythm({"start":1,"end":1.5,"text":"Now","style":"normal"})
    assert out["rhythm"]=="quick"
