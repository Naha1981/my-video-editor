from app.integrations.jev import JevBrowserAgent
from app.integrations.jev.safety import allowed_domain, validate_target_url


def test_jev_disabled_by_default(monkeypatch):
    monkeypatch.delenv("JEV_ENABLED", raising=False)
    agent = JevBrowserAgent(base_url="", api_key="")
    assert agent.enabled is False
    assert agent.configured is False


def test_allowed_domain_matching():
    assert allowed_domain("https://www.example.com/page", "example.com")
    assert not allowed_domain("https://example.org/page", "example.com")


def test_private_targets_are_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.integrations.jev.safety.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("127.0.0.1", 0))],
    )
    try:
        validate_target_url("http://localhost")
    except ValueError as exc:
        assert "private" in str(exc).lower()
    else:
        raise AssertionError("private target should be rejected")
