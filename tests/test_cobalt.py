from app.integrations.cobalt import normalize_candidates


def test_cobalt_redirect_becomes_candidate():
    out = normalize_candidates(
        "https://www.instagram.com/reel/example/",
        {"status": "redirect", "url": "https://cdn.example/video.mp4", "filename": "food.mp4"},
    )
    assert out[0]["provider"] == "cobalt"
    assert out[0]["source_url"].startswith("https://www.instagram.com")


def test_cobalt_picker_preserves_choices_without_auto_selecting():
    out = normalize_candidates(
        "https://www.tiktok.com/@demo/video/1",
        {"status": "picker", "picker": [{"type": "video", "url": "https://cdn.example/a.mp4"}]},
    )
    assert len(out) == 1
    assert out[0]["kind"] == "video"
