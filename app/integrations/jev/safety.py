from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def validate_target_url(url: str) -> str:
    value = (url or "").strip()
    parsed = urlparse(value if "://" in value else "https://" + value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Jev target must be a valid http(s) URL")
    hostname = parsed.hostname.lower().rstrip(".")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(hostname, None)}
    except socket.gaierror as exc:
        raise ValueError(f"Jev target hostname could not be resolved: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise ValueError("Jev refuses private, local, link-local, multicast or reserved targets")
    return parsed._replace(netloc=parsed.netloc).geturl()


def allowed_domain(url: str, allowlist: str) -> bool:
    rules = [item.strip().lower().lstrip(".") for item in (allowlist or "").split(",") if item.strip()]
    if not rules:
        return True
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower().rstrip(".")
    return any(hostname == rule or hostname.endswith("." + rule) for rule in rules)
