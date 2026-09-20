from app.semantic_aggregation import aggregate_semantic_scores


def test_multi_frame_aggregation_resists_single_frame_outlier():
    frames = [
        {"food": 0.80, "experience": 0.10},
        {"food": 0.78, "experience": 0.12},
        {"food": 0.06, "experience": 0.70},
    ]
    out = aggregate_semantic_scores(frames)
    assert out["labels"]["food"] > out["labels"]["experience"]
    assert out["frame_count"] == 3
    assert out["temporal_consistency"] < 1.0


def test_stable_semantic_evidence_has_high_consistency():
    frames = [
        {"food": 0.80, "experience": 0.10},
        {"food": 0.78, "experience": 0.11},
        {"food": 0.82, "experience": 0.09},
    ]
    out = aggregate_semantic_scores(frames)
    assert out["labels"]["food"] > 0.70
    assert out["temporal_consistency"] > 0.8
    assert out["top_labels"][0]["label"] == "food"
