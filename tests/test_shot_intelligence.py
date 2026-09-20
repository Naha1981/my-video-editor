from app.shot_intelligence import intent_fit

def test_intent_fit_uses_strong_per_shot_window():
    analysis = {
        "semantic": {"labels": {"food": 0.2}},
        "semantic_windows": [
            {"labels": {"food": 0.82}},
            {"labels": {"food": 0.31}},
        ],
    }
    assert intent_fit(analysis, "hero_food") == 0.82
