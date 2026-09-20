from jev_worker.api import _validate_url


def test_worker_rejects_local_targets(monkeypatch):
    monkeypatch.setattr(
        "jev_worker.api.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("10.0.0.5", 0))],
    )
    try:
        _validate_url("https://example.com")
    except Exception as exc:
        assert "private" in str(exc).lower()
    else:
        raise AssertionError("private worker target should be rejected")
