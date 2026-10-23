"""Playoff bracket lifecycle: tree creation, series execution, advancement, and standings.

This module drives the single-elimination bracket after seeding:
1. Persists the full bracket tree (random first round plus empty later rounds).
2. Plays each pairing as a best-of-N series of bracket games with alternating sides.
3. Eliminates series losers and randomly pairs the winners into the next round
   once every pairing of a round is finished, until a champion is decided.
4. Derives placement ranks and composite final tournament scores.
"""

from __future__ import annotations

import logging
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, Callable

from sqlalchemy.orm import Session

from server.database import SessionLocal
from server.games import get_active_bot, get_active_game
from server.models import Bot, BracketMatch, Match, TournamentSetting, User
from server.queue import execute_match_job, reset_bracket_speed
from server.tournament import ROUND_NAMES, calculate_final_scores
from server.tournament_config import load_tournament_config

logger = logging.getLogger(__name__)

STATUS_PENDING: str = "pending"
STATUS_RUNNING: str = "running"
STATUS_COMPLETED: str = "completed"

# Round names ordered from the earliest (largest) round to the Final
ROUND_ORDER: list[str] = [
    ROUND_NAMES[size] for size in sorted(ROUND_NAMES, reverse=True)
]

_ROUND_SIZES: dict[str, int] = {name: size for size, name in ROUND_NAMES.items()}
_ROUND_ADVANCE_LOCK = threading.Lock()


def get_round_size(round_name: str) -> int:
    """Return the number of players contesting a round (e.g. 'Semi-Final' -> 4).

    Args:
        round_name: Round label as stored on BracketMatch.round_name.

    Returns:
        Player count for the round, or 0 if the name is not recognised.
    """
    if round_name in _ROUND_SIZES:
        return _ROUND_SIZES[round_name]
    prefix = "Round of "
    if round_name.startswith(prefix) and round_name[len(prefix):].isdigit():
        return int(round_name[len(prefix):])
    return 0


def get_round_name(size: int) -> str:
    """Return the round label for a given player count."""
    return ROUND_NAMES.get(size, f"Round of {size}")


def parse_best_of(match_format: Any) -> int:
    """Parse a series format string such as 'BO3' into its game count.

    Args:
        match_format: Format string ('BO1', 'BO3', 'BO5', ...).

    Returns:
        Odd positive number of games in the series (defaults to 3).
    """
    text = str(match_format or "").strip().upper()
    if text.startswith("BO") and text[2:].isdigit():
        best_of = int(text[2:])
        if best_of >= 1:
            return best_of if best_of % 2 == 1 else best_of + 1
    return 3


def create_bracket(db: Session, matchups: list[dict[str, Any]]) -> list[BracketMatch]:
    """Replace the stored bracket with a fresh tree built from first-round matchups.

    Later rounds are created as empty pending pairings and seeded by Elo after
    the previous round is finished.

    Args:
        db: Active database session.
        matchups: First-round pairings as produced by generate_bracket.

    Returns:
        All newly created BracketMatch rows, earliest round first.
    """
    db.query(BracketMatch).delete()

    created: list[BracketMatch] = []
    for m in matchups:
        player1_id = m["player1_id"]
        player2_id = m["player2_id"]
        # A one-sided first-round pairing is a bye. Mark it complete so its
        # entrant advances with the other winners after the played matches end.
        bye_winner_id = player1_id or player2_id
        is_bye = bool(player1_id) != bool(player2_id)
        bm = BracketMatch(
            round_name=m["round_name"],
            match_index=m["match_index"],
            player1_id=player1_id,
            player2_id=player2_id,
            winner_id=bye_winner_id if is_bye else None,
            status=STATUS_COMPLETED if is_bye else STATUS_PENDING,
        )
        db.add(bm)
        created.append(bm)

    size = len(matchups)
    while size >= 2:
        for idx in range(size // 2):
            bm = BracketMatch(
                round_name=get_round_name(size),
                match_index=idx,
                status=STATUS_PENDING,
            )
            db.add(bm)
            created.append(bm)
        size //= 2

    db.commit()
    for bm in created:
        db.refresh(bm)
    return created


def get_ready_matches(db: Session) -> list[BracketMatch]:
    """Return pending pairings of the earliest unfinished round that have both players."""
    matches = db.query(BracketMatch).order_by(BracketMatch.id.asc()).all()
    round_names = sorted(
        {m.round_name for m in matches},
        key=get_round_size,
        reverse=True,
    )
    for round_name in round_names:
        in_round = [m for m in matches if m.round_name == round_name]
        unfinished = [m for m in in_round if m.status != STATUS_COMPLETED]
        if unfinished:
            return [
                m
                for m in unfinished
                if m.status == STATUS_PENDING and m.player1_id and m.player2_id
            ]
    return []


def _draw_next_round(db: Session, round_name: str) -> None:
    """Randomly pair a finished round's winners into the next round.

    Does nothing until every pairing of the round is completed, so losers are
    all eliminated before the draw. The draw happens only once per round.
    """
    size = get_round_size(round_name)
    if size <= 2:
        return

    current = (
        db.query(BracketMatch)
        .filter(BracketMatch.round_name == round_name)
        .order_by(BracketMatch.match_index.asc())
        .all()
    )
    if any(bm.status != STATUS_COMPLETED or bm.winner_id is None for bm in current):
        return

    next_round = (
        db.query(BracketMatch)
        .filter(BracketMatch.round_name == get_round_name(size // 2))
        .order_by(BracketMatch.match_index.asc())
        .all()
    )
    if any(bm.player1_id or bm.player2_id for bm in next_round):
        return

    winners = [bm.winner_id for bm in current]
    if len(winners) != len(next_round) * 2:
        return

    random.shuffle(winners)
    for idx, bm in enumerate(next_round):
        bm.player1_id = winners[idx * 2]
        bm.player2_id = winners[idx * 2 + 1]


def _active_bot(db: Session, user_id: int) -> Bot | None:
    """Return the player's active bot for the event's active game."""
    return get_active_bot(db, user_id, get_active_game(db))


def _break_tie(player1: User, player2: User) -> int:
    """Pick the better seed (higher Elo, then lower id) when a series is level."""
    if (player1.elo, -player1.id) >= (player2.elo, -player2.id):
        return player1.id
    return player2.id


def play_bracket_series(
    bracket_match_id: int,
    db_factory: Callable[[], Any] | None = None,
) -> int | None:
    """Play one bracket pairing as a best-of-N series and eliminate the loser.

    Sides alternate every game. Games are stored as Match rows flagged
    is_bracket so they never affect Elo. A player without an active bot
    forfeits the series; a level series goes to the better seed. When the last
    pairing of a round finishes, the winners are randomly paired.

    Args:
        bracket_match_id: Primary key of the BracketMatch to play.
        db_factory: Optional callable yielding a SQLAlchemy Session.

    Returns:
        The winning user id, or None if the pairing could not be played.
    """
    session_factory = db_factory or SessionLocal
    db = session_factory()
    try:
        bm = db.query(BracketMatch).filter(BracketMatch.id == bracket_match_id).first()
        if bm is None or bm.status == STATUS_COMPLETED:
            return bm.winner_id if bm else None
        if not bm.player1_id or not bm.player2_id:
            return None
        player1 = db.query(User).filter(User.id == bm.player1_id).first()
        player2 = db.query(User).filter(User.id == bm.player2_id).first()
        if player1 is None or player2 is None:
            return None

        player1_id, player2_id = player1.id, player2.id
        player1_name, player2_name = player1.username, player2.username
        player1_elo, player2_elo = player1.elo, player2.elo
        bot1, bot2 = _active_bot(db, player1_id), _active_bot(db, player2_id)
        bot1_data = (bot1.id, bot1.filepath, bot1.game_type) if bot1 else None
        bot2_data = (bot2.id, bot2.filepath, bot2.game_type) if bot2 else None
        round_name = bm.round_name
        bm.status = STATUS_RUNNING
        bm.score_p1 = 0
        bm.score_p2 = 0
        db.commit()

        bracket_cfg = load_tournament_config().get("tournament", {}).get("final_bracket", {})
        best_of = parse_best_of(bracket_cfg.get("match_format"))
        wins_needed = best_of // 2 + 1
        setting = db.query(TournamentSetting).filter(TournamentSetting.key == "rule_variant").first()
        rule_variant = setting.value if setting and setting.value else "standard"
    except Exception as exc:
        logger.exception("Could not prepare bracket match %d: %s", bracket_match_id, exc)
        return None
    finally:
        db.close()

    score_p1 = score_p2 = 0
    try:
        if bot1_data is not None and bot2_data is not None:
            for game_no in range(best_of):
                swapped = game_no % 2 == 1
                if swapped:
                    first_id, first_name, first_elo, first_bot = player2_id, player2_name, player2_elo, bot2_data
                    second_id, second_name, second_elo, second_bot = player1_id, player1_name, player1_elo, bot1_data
                else:
                    first_id, first_name, first_elo, first_bot = player1_id, player1_name, player1_elo, bot1_data
                    second_id, second_name, second_elo, second_bot = player2_id, player2_name, player2_elo, bot2_data

                game_db = session_factory()
                try:
                    game = Match(
                        player1_id=first_id,
                        player2_id=second_id,
                        bot1_id=first_bot[0],
                        bot2_id=second_bot[0],
                        p1_elo_before=first_elo,
                        p2_elo_before=second_elo,
                        is_bracket=True,
                        bracket_match_id=bracket_match_id,
                        rule_variant=rule_variant,
                        game_type=first_bot[2],
                    )
                    game_db.add(game)
                    game_db.commit()
                    game_id = game.id
                finally:
                    game_db.close()

                result = execute_match_job(game_id, first_bot[1], second_bot[1], db_factory=session_factory)
                if result is None:
                    raise RuntimeError(f"Bracket game {game_id} failed to execute; the series remains pending.")

                winner_code = result.get("winner")
                winner_id = first_id if winner_code == 1 else second_id if winner_code == 2 else None
                winner_name = first_name if winner_code == 1 else second_name if winner_code == 2 else None
                if winner_id == player1_id:
                    score_p1 += 1
                elif winner_id == player2_id:
                    score_p2 += 1

                result_db = session_factory()
                try:
                    current = result_db.query(BracketMatch).filter(BracketMatch.id == bracket_match_id).first()
                    if current is None:
                        raise RuntimeError(f"Bracket pairing {bracket_match_id} disappeared during its series.")
                    current.score_p1 = score_p1
                    current.score_p2 = score_p2
                    game_results = json.loads(current.game_results or "[]")
                    game_results.append({
                        "game_number": game_no + 1,
                        "match_id": game_id,
                        "winner_id": winner_id,
                        "winner_username": winner_name,
                    })
                    current.game_results = json.dumps(game_results, ensure_ascii=False)
                    result_db.commit()
                finally:
                    result_db.close()

                if score_p1 >= wins_needed or score_p2 >= wins_needed:
                    break

        if bot1_data is None and bot2_data is not None:
            winner_id = player2_id
        elif bot2_data is None and bot1_data is not None:
            winner_id = player1_id
        elif score_p1 > score_p2:
            winner_id = player1_id
        elif score_p2 > score_p1:
            winner_id = player2_id
        else:
            winner_id = player1_id if (player1_elo, -player1_id) >= (player2_elo, -player2_id) else player2_id

        final_db = session_factory()
        try:
            current = final_db.query(BracketMatch).filter(BracketMatch.id == bracket_match_id).first()
            if current is None:
                return None
            current.winner_id = winner_id
            current.status = STATUS_COMPLETED
            with _ROUND_ADVANCE_LOCK:
                final_db.flush()
                _draw_next_round(final_db, round_name)
                final_db.commit()
            return winner_id
        finally:
            final_db.close()

    except Exception as exc:
        logger.exception("Error playing bracket match %d: %s", bracket_match_id, exc)
        error_db = session_factory()
        try:
            current = error_db.query(BracketMatch).filter(BracketMatch.id == bracket_match_id).first()
            if current and current.status == STATUS_RUNNING:
                current.status = STATUS_PENDING
                error_db.commit()
        except Exception:
            logger.exception("Could not reset bracket pairing %d after failure", bracket_match_id)
        finally:
            error_db.close()
        return None


def play_bracket_matches(
    bracket_match_ids: list[int],
    db_factory: Callable[[], Any] | None = None,
    max_workers: int = 1,
) -> None:
    """Play independent bracket pairings concurrently up to the configured board count."""
    worker_count = max(1, min(int(max_workers), len(bracket_match_ids) or 1))
    try:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(play_bracket_series, match_id, db_factory)
                for match_id in bracket_match_ids
            ]
            for future in futures:
                future.result()
    finally:
        reset_bracket_speed()


def compute_bracket_standings(matches: list[BracketMatch]) -> dict[int, int]:
    """Derive placement ranks from completed bracket pairings.

    The champion is rank 1 and the losers of a round with N players share
    rank N/2 + 1 (runner-up 2, semi-finalists 3, quarter-finalists 5, ...).

    Args:
        matches: Bracket pairings to evaluate.

    Returns:
        Mapping of user id to placement rank for every eliminated player and the champion.
    """
    standings: dict[int, int] = {}
    for bm in matches:
        if bm.status != STATUS_COMPLETED or bm.winner_id is None:
            continue
        size = get_round_size(bm.round_name)
        if size < 2:
            continue
        loser_id = bm.player2_id if bm.winner_id == bm.player1_id else bm.player1_id
        if loser_id is not None:
            standings[loser_id] = size // 2 + 1
        if size == 2:
            standings[bm.winner_id] = 1
    return standings


def is_bracket_finished(matches: list[BracketMatch]) -> bool:
    """Check whether the Final has been played."""
    return any(
        bm.round_name == get_round_name(2) and bm.status == STATUS_COMPLETED
        for bm in matches
    )


def get_final_results(db: Session) -> list[dict[str, Any]]:
    """Compute composite final scores (normalized Elo + bracket placement) for all players.

    Args:
        db: Active database session.

    Returns:
        Ranked score dictionaries from calculate_final_scores, or an empty list
        while no bracket pairing has been completed.
    """
    matches = db.query(BracketMatch).all()
    standings = compute_bracket_standings(matches)
    if not standings:
        return []

    bracket_cfg = load_tournament_config().get("tournament", {}).get("final_bracket", {})
    users = [
        {"id": u.id, "username": u.username, "elo": u.elo}
        for u in db.query(User).filter(User.is_admin == False).all()  # noqa: E712
    ]
    results = calculate_final_scores(
        users,
        standings,
        weight_elo=float(bracket_cfg.get("weight_elo", 0.5)),
        weight_bracket=float(bracket_cfg.get("weight_bracket", 0.5)),
    )
    for item in results:
        item["bracket_rank"] = standings.get(item["id"])
    return results
