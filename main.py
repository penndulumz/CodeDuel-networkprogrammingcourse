"""Battlecode 9x9 Rock-Paper-Scissors Platform - Root Entrypoint.

Provides a unified single-command launcher (python main.py) that:
1. Parses CLI flags (--host, --port, --reload, --seed-admin).
2. Initializes SQLite database tables (init_db()).
3. Seeds initial admin account (admin / admin123) and starter bots if absent.
4. Displays formatted startup banner with web and API documentation URLs.
5. Launches the Uvicorn ASGI server hosting the FastAPI application.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from sqlalchemy.orm import Session
import uvicorn

from server.database import SessionLocal, init_db
from server.models import Bot, User


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
        default=8000,
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
        # 1. Ensure default admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                is_admin=True,
                elo=1200,
                wins=0,
                losses=0,
                draws=0,
            )
            admin.set_password("admin123")
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("[INFO] Seeded default administrator account: 'admin' / 'admin123'")
        elif not admin.is_admin:
            admin.is_admin = True
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


def print_banner(host: str, port: int) -> None:
    """Print an informative startup banner displaying server endpoints and URLs.

    Args:
        host: Host interface string.
        port: Port integer.
    """
    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
    base_url = f"http://{display_host}:{port}"
    docs_url = f"{base_url}/docs"
    banner = f"""
========================================================================
           BATTLECODE 9x9 ROCK-PAPER-SCISSORS PLATFORM
========================================================================
  Web Interface:      {base_url}
  API Documentation:  {docs_url}
  Admin Dashboard:    {base_url}/admin
  Listening Address:  http://{host}:{port}
========================================================================
"""
    print(banner)


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

    # 3. Print startup banner with direct URL links
    print_banner(parsed.host, parsed.port)

    # 4. Start Uvicorn ASGI server
    uvicorn.run(
        "server.main:app",
        host=parsed.host,
        port=parsed.port,
        reload=parsed.reload,
    )


if __name__ == "__main__":
    main()
