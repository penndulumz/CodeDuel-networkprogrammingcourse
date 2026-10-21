"""Server-side helpers for the multi-game setup.

The platform runs one "active game" at a time (chosen by the admin, stored in
TournamentSetting under the key 'game_type'). Ranked challenges and the bracket
always use each player's active bot for that game, so an event can switch from
Connect Four to Caro without anyone losing their earlier bots.
"""

from __future__ import annotations

import json
from sqlalchemy.orm import Session

from engine.games import DEFAULT_GAME, GAMES, normalize_game_type
from server.models import Bot, TournamentSetting

ACTIVE_GAME_KEY = "game_type"


def get_catalog_games(db: Session) -> list[dict]:
    """List games published by the organizer; initially only RPS is listed."""
    row = db.query(TournamentSetting).filter(TournamentSetting.key == "catalog_games").first()
    try:
        slugs = json.loads(row.value) if row else [DEFAULT_GAME]
    except (ValueError, TypeError):
        slugs = [DEFAULT_GAME]
    if not isinstance(slugs, list):
        slugs = [DEFAULT_GAME]
    return [info for slug, info in GAMES.items() if slug in slugs or slug == DEFAULT_GAME]


def get_active_game(db: Session) -> str:
    """Return the slug of the game currently used for ranked play."""
    setting = db.query(TournamentSetting).filter(TournamentSetting.key == ACTIVE_GAME_KEY).first()
    return normalize_game_type(setting.value if setting else DEFAULT_GAME)


def get_active_game_info(db: Session) -> dict:
    """Return display metadata for the active game."""
    return GAMES[get_active_game(db)]


def get_active_bot(db: Session, user_id: int, game_type: str) -> Bot | None:
    """Return the user's active bot for a given game, if any."""
    return (
        db.query(Bot)
        .filter(
            Bot.user_id == user_id,
            Bot.is_active == True,  # noqa: E712
            Bot.game_type == game_type,
        )
        .first()
    )
