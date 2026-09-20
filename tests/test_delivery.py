from app.delivery import build_delivery_pack, normalize_platforms


def test_platform_aliases_normalize():
    assert normalize_platforms(["instagram", "youtube_shorts", "fb"]) == [
        "reels", "shorts", "facebook"
    ]


def test_delivery_pack_declares_shared_edit_and_platforms(monkeypatch):
    monkeypatch.setattr("app.delivery.ffmpeg_skill_available", lambda: False)
    out = build_delivery_pack(["reels", "linkedin"])
    assert out["engine"] == "native-ffmpeg"
    assert [x["id"] for x in out["platforms"]] == ["reels", "linkedin"]
    assert out["status"] == "ready"
