"""Battlecode 9x9 Rock-Paper-Scissors Platform - Root Entrypoint.

Provides a unified single-command launcher (python main.py) that:
1. Parses CLI flags (--host, --port, --reload, --seed-admin, --tunnel, --public-url).
2. Initializes SQLite database tables (init_db()).
3. Seeds initial admin account (admin / admin123) and starter bots if absent.
4. Displays formatted startup banner with web and API documentation URLs.
5. Optionally opens a Cloudflare quick tunnel so players outside the LAN can join.
6. Launches the Uvicorn ASGI server hosting the FastAPI application.
"""

from __future__ import annotations

import argparse
import atexit
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from typing import List, Optional

from sqlalchemy.orm import Session
import uvicorn

from server.database import SessionLocal, init_db
from server.models import Bot, User
from server.network import get_lan_ip


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line flags for server startup configuration.

    Args:
        args: Optional list of argument strings. If None, sys.argv[1:] is used.

    Returns:
        argparse.Namespace with parsed CLI configuration attributes.
    """
    parser = argparse.ArgumentParser(
        description="Battlecode 9x9 Rock-Paper-Scissors Tournament Platform",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host network interface to bind the HTTP server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port number to bind the HTTP server to.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable live auto-reload for local development.",
    )
    parser.add_argument(
        "--seed-admin",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Seed default admin account and starter bots if not present in the database.",
    )
    parser.add_argument(
        "--tunnel",
        action="store_true",
        default=False,
        help="Expose the server on the Internet through a free Cloudflare quick tunnel "
        "(requires the 'cloudflared' program).",
    )
    parser.add_argument(
        "--public-url",
        type=str,
        default=os.getenv("PUBLIC_URL", ""),
        help="Public address shown to players (e.g. https://arena.example.com) when the "
        "server is behind your own reverse proxy, ngrok or a VPS.",
    )
    return parser.parse_args(args)


def seed_admin_and_starter_bots(db_session: Optional[Session] = None) -> None:
    """Seed the default administrator user and sample bots if not already present.

    Creates:
    - User 'admin' with password 'admin123' and is_admin=True.
    - Uploads/links starter_kit/bot_template.py (active) and starter_kit/heuristic_bot.py.

    Args:
        db_session: Optional SQLAlchemy database session. If None, a new session
            is opened from SessionLocal and automatically closed upon completion.
    """
    close_after = False
    if db_session is None:
        db = SessionLocal()
        close_after = True
    else:
        db = db_session

    try:
        admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123").strip()

        # 1. Demote any rogue admin accounts to preserve strict single-admin invariant
        rogue_admins = (
            db.query(User)
            .filter(User.is_admin == True, User.username != admin_username)
            .all()
        )
        for rogue in rogue_admins:
            rogue.is_admin = False

        # 2. Ensure default admin user exists and is up to date
        admin = db.query(User).filter(User.username == admin_username).first()
        if not admin:
            admin = User(
                username=admin_username,
                is_admin=True,
                elo=1200,
                wins=0,
                losses=0,
                draws=0,
            )
            admin.set_password(admin_password)
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"[INFO] Seeded default administrator account: '{admin_username}'")
        else:
            admin.is_admin = True
            if not admin.verify_password(admin_password):
                admin.set_password(admin_password)
            db.commit()
            db.refresh(admin)

        # 2. Ensure default starter bots exist for the admin
        starter_dir = Path(__file__).resolve().parent / "starter_kit"
        candidate_bots = [
            ("bot_template.py", starter_dir / "bot_template.py", True),
            ("heuristic_bot.py", starter_dir / "heuristic_bot.py", False),
        ]

        existing_bots = {
            b.filename: b for b in db.query(Bot).filter(Bot.user_id == admin.id).all()
        }

        has_active = any(b.is_active for b in existing_bots.values())

        for bot_name, bot_path, default_active in candidate_bots:
            if bot_name not in existing_bots and bot_path.exists():
                is_active = (not has_active) if default_active else False
                new_bot = Bot(
                    user_id=admin.id,
                    filename=bot_name,
                    filepath=str(bot_path.resolve()),
                    is_active=is_active,
                )
                db.add(new_bot)
                if is_active:
                    has_active = True
                print(f"[INFO] Seeded starter bot '{bot_name}' for administrator.")

        # Ensure at least one bot is active if any bots exist
        admin_bots = db.query(Bot).filter(Bot.user_id == admin.id).all()
        if admin_bots and not any(b.is_active for b in admin_bots):
            admin_bots[0].is_active = True

        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"[WARNING] Database seeding encountered an error: {exc}", file=sys.stderr)
        raise
    finally:
        if close_after:
            db.close()


def print_banner(host: str, port: int, public_url: str = "") -> None:
    """Print an informative startup banner displaying server endpoints and URLs.

    Args:
        host: Host interface string.
        port: Port integer.
        public_url: Optional Internet (WAN) address to advertise.
    """
    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
    base_url = f"http://{display_host}:{port}"
    docs_url = f"{base_url}/docs"
    admin_url = f"{base_url}/admin"
    lan_ip = get_lan_ip()
    lan_url = f"http://{lan_ip}:{port}"

    banner = f"""
========================================================================
           BATTLECODE 9x9 ROCK-PAPER-SCISSORS PLATFORM
========================================================================
  Local URL:          {base_url}
  LAN Network URL:    {lan_url}  (Share with other machines on LAN)
  Admin Dashboard:    {admin_url}
  API Documentation:  {docs_url}
  Listening Interface:http://{host}:{port}
========================================================================
"""
    if public_url:
        banner += f"""  Public WAN URL:     {public_url}  (Share with players on the Internet)
========================================================================
"""
    print(banner)


TUNNEL_URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def parse_tunnel_url(line: str) -> Optional[str]:
    """Extract the public https://*.trycloudflare.com address from cloudflared output."""
    match = TUNNEL_URL_PATTERN.search(line)
    return match.group(0) if match else None


def start_cloudflare_tunnel(port: int, wait_seconds: float = 25.0) -> Optional[str]:
    """Start a Cloudflare quick tunnel to localhost:port and return its public URL.

    Quick tunnels need no account or router configuration, work behind school
    NAT/firewalls (outbound HTTPS only) and give a valid HTTPS certificate,
    which is why they are the recommended way to open a LAN event to the
    Internet. The cloudflared process is stopped automatically on exit.

    Returns:
        The public URL, or None if cloudflared is missing or did not report one.
    """
    binary = shutil.which("cloudflared")
    if binary is None:
        print(
            "[WARNING] --tunnel needs 'cloudflared'. Install it from "
            "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/ "
            "(Windows: winget install --id Cloudflare.cloudflared). Continuing on LAN only.",
            file=sys.stderr,
        )
        return None

    proc = subprocess.Popen(
        [binary, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    atexit.register(proc.terminate)

    found: dict[str, str] = {}

    def _read_output() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            url = parse_tunnel_url(line)
            if url and "url" not in found:
                found["url"] = url

    threading.Thread(target=_read_output, daemon=True).start()
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline and "url" not in found and proc.poll() is None:
        time.sleep(0.2)

    if "url" not in found:
        print("[WARNING] cloudflared did not report a public URL; continuing on LAN only.",
              file=sys.stderr)
        return None
    return found["url"]


def main(args: Optional[List[str]] = None) -> None:
    """Application entrypoint coordinating initialization and server execution.

    Args:
        args: Optional command line argument list. If None, sys.argv[1:] is used.
    """
    parsed = parse_args(args)

    # 1. Initialize SQLite schema
    init_db()

    # 2. Seed initial admin account and default bots if enabled
    if parsed.seed_admin:
        seed_admin_and_starter_bots()

    # 3. Optional WAN exposure: an explicit public URL or a Cloudflare quick tunnel
    public_url = parsed.public_url.strip().rstrip("/")
    if parsed.tunnel:
        public_url = start_cloudflare_tunnel(parsed.port) or public_url
    if public_url:
        # Read by server.network.get_public_url to show players the shareable link
        os.environ["PUBLIC_URL"] = public_url

    # 4. Print startup banner with direct URL links
    if public_url:
        print_banner(parsed.host, parsed.port, public_url)
    else:
        print_banner(parsed.host, parsed.port)

    # 5. Start Uvicorn ASGI server. Uvicorn trusts X-Forwarded-Proto/For from
    # the proxies listed in FORWARDED_ALLOW_IPS (default 127.0.0.1, which covers
    # a local cloudflared), so requests through an HTTPS tunnel are seen as https.
    uvicorn.run(
        "server.main:app",
        host=parsed.host,
        port=parsed.port,
        reload=parsed.reload,
    )


if __name__ == "__main__":
    main()
