"""Network helpers for LAN and WAN (Internet) deployments.

When the server sits behind an HTTPS tunnel or reverse proxy (Cloudflare
Tunnel, ngrok, Nginx...), the browser talks HTTPS to the proxy while the proxy
talks plain HTTP to us. Uvicorn's proxy-header support rewrites request.url
from X-Forwarded-Proto/Host for trusted proxies, so the helpers below can
tell which address players actually used.
"""

from __future__ import annotations

import os
import socket

from fastapi import Request

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}


def get_lan_ip() -> str:
    """Detect the local machine's primary IPv4 address on the local network (LAN).

    Attempts a UDP probe connection to resolve the outbound network interface IP.
    Falls back to hostname resolution or '127.0.0.1' if disconnected or unavailable.

    Returns:
        str: IPv4 address string (e.g. '192.168.1.15').
    """
    probe_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probe_socket.settimeout(0.5)
    ip = "127.0.0.1"
    try:
        # Probe does not send network packets; resolves local routing table
        probe_socket.connect(("8.8.8.8", 80))
        ip = probe_socket.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        probe_socket.close()

    if not ip or ip.startswith("127."):
        try:
            host_ip = socket.gethostbyname(socket.gethostname())
            if host_ip and not host_ip.startswith("127."):
                ip = host_ip
        except Exception:
            pass

    return ip or "127.0.0.1"


def get_public_url(request: Request | None = None) -> str:
    """Return the address players should use to reach this server.

    Priority: the PUBLIC_URL environment variable (set by `main.py --tunnel` or
    by the organiser), then the scheme and host of the current request, with
    localhost replaced by the machine's LAN address.
    """
    configured = os.getenv("PUBLIC_URL", "").strip().rstrip("/")
    if configured:
        return configured
    if request is None:
        return ""
    host = request.url.hostname or ""
    if host in LOCAL_HOSTS:
        # The organiser is browsing on the server itself: advertise the LAN
        # address instead, since "localhost" is useless on other machines.
        port = f":{request.url.port}" if request.url.port else ""
        return f"{request.url.scheme}://{get_lan_ip()}{port}"
    return f"{request.url.scheme}://{request.url.netloc}"


def should_use_secure_cookie(request: Request) -> bool:
    """Decide whether the session cookie must carry the Secure flag.

    COOKIE_SECURE=true/false forces the behaviour. When it is unset ("auto"),
    the cookie is Secure only for HTTPS requests, so the same build works on
    plain-HTTP LAN parties and behind an HTTPS tunnel without reconfiguring.
    """
    setting = os.getenv("COOKIE_SECURE", "auto").strip().lower()
    if setting in ("true", "1", "yes"):
        return True
    if setting in ("false", "0", "no"):
        return False
    return request.url.scheme == "https"
