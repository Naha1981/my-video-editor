from app.storyboard import transition_for

def test_cta_transition_uses_fade():
    assert transition_for({"creative_intent":"proof"},{"creative_intent":"cta","type":"clip"},2) == "fade"

def test_normal_story_uses_hard_cut():
    assert transition_for({"creative_intent":"craft"},{"creative_intent":"experience","type":"clip"},1) == "hard_cut"
