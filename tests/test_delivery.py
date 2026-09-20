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


def test_final_qa_blocks_missing_required_coverage(tmp_path):
    from app.delivery import validate_final_plan
    out = validate_final_plan(
        {"timeline": [{"type": "clip", "clip_id": "a", "duration": 2}], "settings": {"duration": 2},
         "footage_gaps": {"required_gap_count": 1}},
        {"a": tmp_path / "a.mp4"},
        approved_stock_ids=set(),
    )
    assert out["status"] == "blocked"
    assert any(x["id"] == "required_coverage" and x["status"] == "block" for x in out["checks"])


def test_final_qa_passes_clean_native_timeline(tmp_path):
    from app.delivery import validate_final_plan
    source = tmp_path / "a.mp4"
    source.write_bytes(b"x")
    out = validate_final_plan(
        {"timeline": [{"type": "clip", "clip_id": "a", "duration": 2}], "settings": {"duration": 2},
         "footage_gaps": {"required_gap_count": 0}},
        {"a": source},
        approved_stock_ids=set(),
    )
    assert out["status"] == "ready"
