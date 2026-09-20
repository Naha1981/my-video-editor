from app.pacing import align_cut_boundaries


def test_cut_moves_to_nearby_safe_music_beat():
    timeline = [
        {"duration": 2.0, "speech_ranges_output": []},
        {"duration": 3.0, "speech_ranges_output": []},
    ]
    out, decisions = align_cut_boundaries(timeline, [2.22], total_duration=5)
    assert abs(out[0]["duration"] - 2.22) < 0.01
    assert abs(out[1]["duration"] - 2.78) < 0.01
    assert decisions[0]["status"] == "beat_aligned"


def test_dialogue_overrides_nearby_beat():
    timeline = [
        {"duration": 2.0, "speech_ranges_output": [[1.7, 2.3]]},
        {"duration": 3.0, "speech_ranges_output": []},
    ]
    out, decisions = align_cut_boundaries(timeline, [2.1], total_duration=5)
    assert abs(out[0]["duration"] - 2.0) < 0.01
    assert decisions[0]["status"] in {"speech_preserved", "speech_safe"}


def test_beat_alignment_preserves_total_duration():
    timeline = [
        {"duration": 1.8, "speech_ranges_output": []},
        {"duration": 2.2, "speech_ranges_output": []},
        {"duration": 1.5, "speech_ranges_output": []},
    ]
    out, _ = align_cut_boundaries(timeline, [1.95, 4.05], total_duration=5.5)
    assert abs(sum(x["duration"] for x in out) - 5.5) < 0.01
