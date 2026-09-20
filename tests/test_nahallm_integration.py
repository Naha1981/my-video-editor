import os

from app.integrations.nahallm import NahaLLMClient
from app.services.mission_compiler import compile_asset_mission


def test_nahallm_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NAHALLM_ENABLED", raising=False)
    client = NahaLLMClient(base_url="", api_key="")
    assert client.enabled is False
    assert client.configured is False


def test_mission_compiler_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setenv("NAHALLM_ENABLED", "0")
    mission, trace = compile_asset_mission("https://example.com", "Collect the logo")
    assert mission.source_url == "https://example.com"
    assert "logo" in mission.goal.lower()
    assert trace["source"] == "deterministic_fallback"
