"""Automatic bot grader: plays a bot against a fixed ladder of reference opponents.

This gives students (and teachers) an objective, repeatable score out of 10
without needing a running tournament, other players, or an internet connection:

    python starter_kit/grade.py my_bot.py --game connect4

The same function powers the web "Tự chấm điểm" page, so a score obtained
offline matches the score shown on the server.

Scoring:
- The bot first has to pass the AST sandbox; otherwise the score is 0.
- Against each reference opponent the bot plays `games_per_opponent` games,
  alternating who moves first. A win counts 1 point, a draw 0.5, a loss 0.
- Each opponent has a weight; the final score is
      10 * sum(weight * points_ratio) / sum(weight)
  rounded to one decimal place.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from engine.games import GAME_CARO, GAME_CONNECT4, GAME_RPS9, GAMES, normalize_game_type
from engine.runner import run_match
from engine.sandbox import validate_bot_file

REPO_ROOT = Path(__file__).resolve().parent.parent
STARTER = REPO_ROOT / "starter_kit"
BOSSES = REPO_ROOT / "server" / "bosses"

# Reference ladders ordered from easiest to hardest: (label, bot path, weight).
GRADING_LADDERS: dict[str, list[tuple[str, Path, int]]] = {
    GAME_CONNECT4: [
        ("Random (Lv1)", STARTER / "opponents" / "connect4_random.py", 4),
        ("Heuristic (Lv2)", STARTER / "connect4_bot.py", 6),
    ],
    GAME_CARO: [
        ("Random (Lv1)", STARTER / "opponents" / "caro_random.py", 4),
        ("Heuristic (Lv2)", STARTER / "caro_bot.py", 6),
    ],
    GAME_RPS9: [
        ("Novice (Lv1)", BOSSES / "novice_bot.py", 3),
        ("Heuristic (Lv2)", STARTER / "heuristic_bot.py", 3),
        ("Rusher (Lv3)", BOSSES / "rusher_bot.py", 4),
    ],
}

# Score bands shown to students next to the number.
GRADE_BANDS: list[tuple[float, str]] = [
    (9.0, "Xuất sắc"),
    (7.0, "Giỏi"),
    (5.0, "Khá"),
    (3.0, "Trung bình"),
    (0.0, "Cần cố gắng"),
]


def grade_label(score: float) -> str:
    """Return the Vietnamese band label for a score out of 10."""
    for threshold, label in GRADE_BANDS:
        if score >= threshold:
            return label
    return GRADE_BANDS[-1][1]


def grade_bot(
    bot_path: str | Path,
    game_type: str,
    games_per_opponent: int = 4,
    timeout_per_turn: float = 1.0,
    max_turns: int = 200,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Grade a bot file against the reference ladder of a game.

    Args:
        bot_path: Path to the student's bot file.
        game_type: Game slug (see engine.games.GAMES).
        games_per_opponent: Games per opponent; sides alternate each game.
        timeout_per_turn: Per-move time limit in seconds.
        max_turns: Turn limit for RPS 9x9 (grid games end on their own).
        progress: Optional callback receiving a short status line per game.

    Returns:
        A report dict with 'score' (0..10), 'label', 'valid', 'error' and a
        per-opponent breakdown under 'opponents'.
    """
    game_type = normalize_game_type(game_type)
    games_per_opponent = max(2, int(games_per_opponent))
    report: dict[str, Any] = {
        "game_type": game_type,
        "game_name": GAMES[game_type]["name_vi"],
        "score": 0.0,
        "label": grade_label(0.0),
        "valid": False,
        "error": None,
        "opponents": [],
    }

    is_valid, error = validate_bot_file(bot_path)
    if not is_valid:
        report["error"] = f"Bot không qua được kiểm tra sandbox: {error}"
        return report
    report["valid"] = True

    weighted = 0.0
    total_weight = 0
    for label, opponent_path, weight in GRADING_LADDERS[game_type]:
        row = {"name": label, "weight": weight, "wins": 0, "draws": 0, "losses": 0,
               "points": 0.0, "games": games_per_opponent, "errors": []}
        for game_no in range(games_per_opponent):
            bot_first = game_no % 2 == 0
            p1, p2 = (bot_path, opponent_path) if bot_first else (opponent_path, bot_path)
            result = run_match(
                str(p1), str(p2),
                max_turns=max_turns,
                timeout_per_turn=timeout_per_turn,
                game_type=game_type,
            )
            me = 1 if bot_first else 2
            if result["winner"] == me:
                row["wins"] += 1
                outcome = "thắng"
            elif result["winner"] is None:
                row["draws"] += 1
                outcome = "hòa"
            else:
                row["losses"] += 1
                outcome = "thua"
                my_error = result.get("bot1_error" if me == 1 else "bot2_error")
                if my_error and my_error not in row["errors"]:
                    row["errors"].append(my_error)
            if progress:
                side = "đi trước" if bot_first else "đi sau"
                progress(f"{label}: ván {game_no + 1}/{games_per_opponent} ({side}) - {outcome}"
                         f" [{result['win_reason']}]")

        row["points"] = row["wins"] + 0.5 * row["draws"]
        ratio = row["points"] / games_per_opponent
        row["ratio"] = round(ratio, 3)
        weighted += weight * ratio
        total_weight += weight
        report["opponents"].append(row)

    score = round(10.0 * weighted / total_weight, 1) if total_weight else 0.0
    report["score"] = score
    report["label"] = grade_label(score)
    return report
