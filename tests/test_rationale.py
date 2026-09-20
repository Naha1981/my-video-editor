from app.rationale import build_edit_rationale

def test_rationale_explains_creative_intent():
    rows=build_edit_rationale({"shots_ranked":[{"id":"a","reasons":["visual quality 90"]}],"timeline":[{"type":"clip","clip_id":"a","filename":"hero.mp4","creative_intent":"hero_food","intent_fit":0.9}]})
    assert rows[0]["confidence"]=="high"
    assert "hero food" in rows[0]["decision"]
    assert "90%" in rows[0]["why"]
