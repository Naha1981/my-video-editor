from __future__ import annotations

import mimetypes
import os
import socket
import ipaddress
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

from ..stock_ingest import register_stock_asset


MEDIA_LIMIT_BYTES = int(os.getenv("NAHAVIDEO_ASSET_MAX_BYTES", str(80 * 1024 * 1024)))
ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}


def _resolve_public(host: str) -> set[str]:
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise ValueError(f"Asset hostname could not be resolved: {host}") from exc
    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise ValueError("Asset URL resolves to a private/local/reserved address")
    return addresses


def _allowed(url: str, source_url: str) -> bool:
    parsed = urlparse(url)
    source = urlparse(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    _resolve_public(parsed.hostname)
    asset_host = parsed.hostname.lower().rstrip(".")
    source_host = (source.hostname or "").lower().rstrip(".")

    configured = {
        item.strip().lower().lstrip(".")
        for item in os.getenv("NAHAVIDEO_ASSET_ALLOWED_DOMAINS", "").split(",")
        if item.strip()
    }

    if asset_host == source_host or asset_host.endswith("." + source_host):
        return True
    return any(asset_host == rule or asset_host.endswith("." + rule) for rule in configured)


class _SafeRedirects(HTTPRedirectHandler):
    def __init__(self, source_url: str):
        super().__init__()
        self.source_url = source_url

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _allowed(newurl, self.source_url):
            raise ValueError("Asset redirect leaves the approved asset domains")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _filename(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov"}:
        return "asset" + suffix
    return "asset" + ALLOWED_TYPES.get(content_type.split(";", 1)[0].lower(), mimetypes.guess_extension(content_type) or "")


def collect_public_assets(
    assets: list[dict],
    *,
    source_url: str,
    media_dir: Path | None = None,
    max_assets: int = 12,
) -> list[dict]:
    media_dir = media_dir or (Path(__file__).resolve().parents[2] / "media")
    media_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    opener = build_opener(_SafeRedirects(source_url))

    for asset in assets[:max_assets]:
        url = str(asset.get("url") or "").strip()
        if asset.get("kind") not in {"image", "video", "direct_media"} or not url:
            continue
        try:
            if not _allowed(url, source_url):
                results.append({
                    "url": url,
                    "status": "skipped",
                    "reason": "asset domain not approved",
                })
                continue

            request = Request(
                url,
                headers={
                    "User-Agent": "NahaVideo/0.22 (+public-asset-collector)",
                    "Accept": "image/avif,image/webp,image/apng,image/*,video/mp4,video/webm,video/*;q=0.8,*/*;q=0.1",
                },
            )
            with opener.open(request, timeout=20) as response:
                content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
                if content_type not in ALLOWED_TYPES:
                    results.append({
                        "url": url,
                        "status": "skipped",
                        "reason": f"unsupported content type: {content_type or 'unknown'}",
                    })
                    continue
                length = response.headers.get("Content-Length")
                if length and int(length) > MEDIA_LIMIT_BYTES:
                    results.append({
                        "url": url,
                        "status": "skipped",
                        "reason": "asset exceeds size limit",
                    })
                    continue

                data = bytearray()
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > MEDIA_LIMIT_BYTES:
                        raise ValueError("asset exceeds size limit")

                suffix = ALLOWED_TYPES[content_type]
                asset_id = __import__("uuid").uuid4().hex[:12]
                path = media_dir / f"{asset_id}{suffix}"
                path.write_bytes(data)

            if content_type.startswith("video/"):
                # Downloaded stock/B-roll is never auto-approved. Preserve provenance.
                provenance = register_stock_asset(
                    path,
                    beat=str(asset.get("purpose") or "supporting"),
                    intent=str(asset.get("intent") or "cta"),
                    provider=str(asset.get("provider") or "browser-scout"),
                    source_url=url,
                    license_name=str(asset.get("license_name") or ""),
                    attribution=str(asset.get("attribution") or ""),
                    approved=False,
                )
                results.append({
                    **asset,
                    "id": asset_id,
                    "filename": path.name,
                    "status": "collected",
                    "provenance": provenance,
                })
            else:
                results.append({
                    **asset,
                    "id": asset_id,
                    "filename": path.name,
                    "status": "collected",
                    "provenance_status": "source_observed_license_unverified",
                })
        except Exception as exc:
            results.append({
                "url": url,
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
            })
    return results
