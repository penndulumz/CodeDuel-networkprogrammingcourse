"""Game registry: every game the platform can run, keyed by a stable slug.

The original RPS 9x9 chess engine (engine/game.py) stays untouched; it is simply
registered here next to the newer grid games so the server, runner, starter kit
and web UI can all ask "which games exist?" from one place.

To add a new game:
1. Implement its rules (see engine/games/grid.py for a compact example).
2. Add an entry to GAMES below with its display metadata.
3. Teach engine/runner.py how to run it (grid games are handled generically).
"""

from __future__ import annotations

from typing import Any

from engine.games.grid import CaroGame, Connect4Game, GridGame

GAME_RPS9: str = "rps9x9"
GAME_CONNECT4: str = "connect4"
GAME_CARO: str = "caro"

DEFAULT_GAME: str = GAME_RPS9

# Display metadata shared by the web UI, guides and starter kit.
# 'level' is a rough difficulty hint for first-year students (1 = easiest).
GAMES: dict[str, dict[str, Any]] = {
    GAME_CONNECT4: {
        "slug": GAME_CONNECT4,
        "name": "Connect Four",
        "name_vi": "Thả 4 quân",
        "tagline": "Thả quân vào cột, nối 4 quân liền nhau là thắng.",
        "board": "6 × 7",
        "move_format": "int — chỉ số cột 0..6",
        "level": 1,
        "level_label": "Dễ — hợp người mới",
        "icon": "C4",
        "rows": 6,
        "cols": 7,
    },
    GAME_CARO: {
        "slug": GAME_CARO,
        "name": "Caro",
        "name_vi": "Cờ Caro (Gomoku)",
        "tagline": "Đặt quân bất kỳ đâu trên bàn 15×15, 5 quân thẳng hàng là thắng.",
        "board": "15 × 15",
        "move_format": "(row, col) — ô trống bất kỳ",
        "level": 2,
        "level_label": "Trung bình",
        "icon": "X5",
        "rows": 15,
        "cols": 15,
    },
    GAME_RPS9: {
        "slug": GAME_RPS9,
        "name": "RPS Chess 9x9",
        "name_vi": "Cờ Oẳn Tù Tì 9×9",
        "tagline": "9 quân Búa-Bao-Kéo mỗi bên, chạm ô đích hoặc diệt sạch một loại quân.",
        "board": "9 × 9",
        "move_format": "((from_row, from_col), (to_row, to_col))",
        "level": 3,
        "level_label": "Nâng cao",
        "icon": "RPS",
        "rows": 9,
        "cols": 9,
    },
}

SUPPORTED_GAMES: list[str] = list(GAMES.keys())

_GRID_GAMES: dict[str, type[GridGame]] = {
    GAME_CONNECT4: Connect4Game,
    GAME_CARO: CaroGame,
}


def normalize_game_type(value: Any) -> str:
    """Return a supported game slug, falling back to the default game."""
    if isinstance(value, str) and value.strip() in GAMES:
        return value.strip()
    return DEFAULT_GAME


def is_grid_game(game_type: str) -> bool:
    """True for stone-placement games handled by engine.games.grid."""
    return game_type in _GRID_GAMES


def create_grid_game(game_type: str) -> GridGame:
    """Instantiate a fresh grid game by slug.

    Raises:
        ValueError: If the slug is not a grid game.
    """
    try:
        return _GRID_GAMES[game_type]()
    except KeyError as exc:
        raise ValueError(f"Unknown grid game: {game_type}") from exc


def list_games() -> list[dict[str, Any]]:
    """Return game metadata ordered from easiest to hardest."""
    return sorted(GAMES.values(), key=lambda g: g["level"])


__all__ = [
    "GAME_RPS9",
    "GAME_CONNECT4",
    "GAME_CARO",
    "DEFAULT_GAME",
    "GAMES",
    "SUPPORTED_GAMES",
    "CaroGame",
    "Connect4Game",
    "GridGame",
    "create_grid_game",
    "is_grid_game",
    "list_games",
    "normalize_game_type",
]
