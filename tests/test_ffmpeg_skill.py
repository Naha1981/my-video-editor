from pathlib import Path

from app.ffmpeg_skill import find_skill_root, verify_output


def test_ffmpeg_skill_discovery_uses_configured_home(tmp_path, monkeypatch):
    root = tmp_path / "skill"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "probe.py").write_text("print('{}')", encoding="utf-8")
    monkeypatch.setenv("NAHAVIDEO_FFMPEG_SKILL_HOME", str(root))
    assert find_skill_root() == root


def test_verify_output_falls_back_when_skill_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("NAHAVIDEO_FFMPEG_SKILL_HOME", str(tmp_path / "missing"))
    output = tmp_path / "final.mp4"
    output.write_bytes(b"video")
    result = verify_output(output, "reels")
    assert result["status"] == "fallback_only"
    assert result["available"] is False
