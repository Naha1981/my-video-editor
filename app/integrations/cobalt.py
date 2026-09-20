from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin


class CobaltError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.getenv("NAHAVIDEO_COBALT_API_URL", "").strip())


def _api_url() -> str:
    value = os.getenv("NAHAVIDEO_COBALT_API_URL", "").strip()
    if not value:
        raise CobaltError("Cobalt is not configured")
    return value.rstrip("/") + "/"


def request_media(source_url: str, *, video_quality: str = "1080") -> dict:
    """Ask a self-hosted Cobalt instance for media; never uses a public instance implicitly."""
    source_url = str(source_url or "").strip()
    if not source_url.startswith(("http://", "https://")):
        raise CobaltError("Only HTTP(S) source URLs are supported")

    payload = {
        "url": source_url,
        "downloadMode": "auto",
        "videoQuality": video_quality,
        "filenameStyle": "pretty",
        "disableMetadata": False,
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    api_key = os.getenv("NAHAVIDEO_COBALT_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Api-Key {api_key}"

    request = Request(
        _api_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise CobaltError(f"Cobalt request failed: {type(exc).__name__}: {exc}") from exc

    status = result.get("status")
    if status == "error":
        raise CobaltError(str((result.get("error") or {}).get("code") or "Cobalt returned an error"))
    return result


def normalize_candidates(source_url: str, response: dict) -> list[dict]:
    status = response.get("status")
    if status in {"redirect", "tunnel"} and response.get("url"):
        return [{
            "kind": "video",
            "url": response["url"],
            "filename": response.get("filename") or "cobalt-media.mp4",
            "source_url": source_url,
            "provider": "cobalt",
        }]
    if status == "picker":
        return [
            {
                "kind": item.get("type", "video"),
                "url": item.get("url"),
                "thumbnail": item.get("thumb"),
                "source_url": source_url,
                "provider": "cobalt",
            }
            for item in response.get("picker", [])
            if item.get("url")
        ]
    if status == "local-processing":
        return [
            {
                "kind": "video",
                "url": tunnel,
                "filename": (response.get("output") or {}).get("filename") or "cobalt-media.mp4",
                "source_url": source_url,
                "provider": "cobalt",
            }
            for tunnel in response.get("tunnel", [])
        ]
    return []


def cobalt_host() -> str:
    from urllib.parse import urlparse
    return urlparse(_api_url()).hostname or ""


def candidate_download_allowed(url: str) -> bool:
    """Only permit candidate downloads from the configured Cobalt host or explicit allowlist."""
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if not host:
        return False
    configured_hosts = {
        cobalt_host().lower().rstrip("."),
        *{
            item.strip().lower().lstrip(".").rstrip(".")
            for item in os.getenv("NAHAVIDEO_COBALT_DOWNLOAD_DOMAINS", "").split(",")
            if item.strip()
        },
    }
    return host in configured_hosts or any(host.endswith("." + item) for item in configured_hosts if item)
