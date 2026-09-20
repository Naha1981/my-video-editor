from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


def enabled() -> bool:
    return bool(os.getenv("NAHAVIDEO_AUTH_PASSWORD", "").strip() and secret())


def secret() -> bytes:
    return os.getenv("NAHAVIDEO_AUTH_SECRET", "nahavideo-change-this-secret").encode("utf-8")


def _sign(payload: str) -> str:
    digest = hmac.new(secret(), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def issue_session(password: str, ttl_seconds: int = 86400) -> str | None:
    expected = os.getenv("NAHAVIDEO_AUTH_PASSWORD", "")
    if not expected or not hmac.compare_digest(str(password or ""), expected):
        return None
    payload = json.dumps({"exp": int(time.time()) + ttl_seconds}, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return encoded + "." + _sign(encoded)


def valid_session(token: str | None) -> bool:
    if not enabled() or not token or "." not in token:
        return not enabled()
    encoded, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(_sign(encoded), signature):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded + "==").decode("utf-8"))
        return int(payload.get("exp", 0)) > int(time.time())
    except Exception:
        return False


def cookie_options(request) -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": request.url.scheme == "https",
        "samesite": "lax",
        "max_age": 86400,
        "path": "/",
    }
