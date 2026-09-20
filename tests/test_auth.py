from app.auth import issue_session, valid_session

def test_auth_disabled_accepts_missing_session(monkeypatch):
    monkeypatch.delenv("NAHAVIDEO_AUTH_PASSWORD", raising=False)
    assert valid_session(None) is True

def test_auth_session_round_trip(monkeypatch):
    monkeypatch.setenv("NAHAVIDEO_AUTH_PASSWORD", "secret")
    monkeypatch.setenv("NAHAVIDEO_AUTH_SECRET", "test-secret")
    token=issue_session("secret", ttl_seconds=60)
    assert token
    assert valid_session(token) is True
    assert valid_session(token+"x") is False
