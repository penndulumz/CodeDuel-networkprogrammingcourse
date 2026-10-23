"""Asynchronous match execution queue and worker jobs.

This module processes queued matches by executing bot matches in isolated
subprocesses via engine.runner, saving replay logs, updating user Elo ratings
and match statistics, and committing outcomes to the database.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import threading
import time
from typing import Any, Callable

from engine.game import MAX_TURNS
from engine.games import normalize_game_type
from engine.runner import run_match, save_replay
from server.database import DATA_DIR, SessionLocal
from server.models import Match, TournamentSetting, User
from server.tournament import apply_elo_change, calculate_elo_delta
from server.tournament_config import load_tournament_config

logger = logging.getLogger(__name__)
BRACKET_MOVE_DISPLAY_DELAY_SECONDS = 0.45
_bracket_fast_mode = threading.Event()


def speed_up_bracket_round() -> None:
    """Skip spectator pacing delays for the currently running bracket round."""
    _bracket_fast_mode.set()


def reset_bracket_speed() -> None:
    """Restore normal spectator pacing after a bracket round finishes."""
    _bracket_fast_mode.clear()


def _get_setting_value(db, key: str, default: Any, caster: Callable[[str], Any]) -> Any:
    """Retrieve and cast a tournament setting value from the database with a default fallback."""
    try:
        setting = db.query(TournamentSetting).filter(TournamentSetting.key == key).first()
        if setting and setting.value is not None:
            return caster(setting.value)
    except Exception:
        pass
    return default


def execute_match_job(
    match_id: int,
    bot1_path: str,
    bot2_path: str,
    db_factory: Callable[[], Any] | None = None,
) -> dict[str, Any] | None:
    """Execute a queued match job, calculate Elo changes, and save replay artifacts.

    Args:
        match_id: Primary key of the Match record to execute.
        bot1_path: File system path to the Player 1 Python bot script.
        bot2_path: File system path to the Player 2 Python bot script.
        db_factory: Optional callable yielding a SQLAlchemy Session (defaults to SessionLocal).

    Returns:
        The completed match result dictionary, or None if execution failed.
    """
    session_factory = db_factory or SessionLocal
    db = session_factory()
    try:
        match = db.query(Match).filter(Match.id == match_id).first()
        if match is None:
            logger.error("Match with id %d not found in database.", match_id)
            return None
        player1 = db.query(User).filter(User.id == match.player1_id).first()
        player2 = db.query(User).filter(User.id == match.player2_id).first()
        if player1 is None or player2 is None:
            logger.error("Players for match %d not found.", match_id)
            return None

        # Copy the values needed by the runner, then release this connection.
        player1_id, player2_id = player1.id, player2.id
        player1_name, player2_name = player1.username, player2.username
        is_bracket = match.is_bracket
        match_variant = match.rule_variant
        game_type = normalize_game_type(match.game_type)
        config = load_tournament_config()
        t_cfg = config.get("tournament", {})
        elo_cfg = t_cfg.get("elo", {})
        rules_cfg = t_cfg.get("match_rules", {})
        multiplier_x = _get_setting_value(db, "daily_multiplier_x", elo_cfg.get("daily_multiplier_x", 1.5), float)
        k_factor = _get_setting_value(db, "k_factor", elo_cfg.get("k_factor", 32), int)
        max_turns = max(10, min(MAX_TURNS, _get_setting_value(db, "max_turns", rules_cfg.get("max_turns", MAX_TURNS), int)))
        timeout_seconds = _get_setting_value(db, "turn_timeout_seconds", rules_cfg.get("turn_timeout_seconds", 1.0), float)
        db_variant = _get_setting_value(db, "rule_variant", None, str)
        if match_variant and match_variant != "standard":
            rule_variant = match_variant
        else:
            rule_variant = db_variant or match_variant or "standard"
    except Exception as exc:
        logger.exception("Could not prepare match %d: %s", match_id, exc)
        return None
    finally:
        db.close()

    try:
        p1_meta = {"id": player1_id, "username": player1_name, "match_id": match_id}
        p2_meta = {"id": player2_id, "username": player2_name, "match_id": match_id}

        def save_live_progress(moves: list[dict[str, Any]]) -> None:
            progress_db = session_factory()
            try:
                live_match = progress_db.query(Match).filter(Match.id == match_id).first()
                if live_match is not None:
                    live_match.live_moves = json.dumps(moves, ensure_ascii=False)
                    live_match.total_turns = len(moves)
                    progress_db.commit()
            except Exception:
                logger.exception("Failed to persist live progress for bracket match %d", match_id)
            finally:
                progress_db.close()
            if not _bracket_fast_mode.is_set():
                time.sleep(BRACKET_MOVE_DISPLAY_DELAY_SECONDS)

        match_result = run_match(
            bot1_path=bot1_path,
            bot2_path=bot2_path,
            max_turns=max_turns,
            timeout_per_turn=timeout_seconds,
            player1_info=p1_meta,
            player2_info=p2_meta,
            variant=rule_variant,
            game_type=game_type,
            progress_callback=save_live_progress if is_bracket else None,
        )

        replays_dir = (DATA_DIR / "replays").resolve()
        replays_dir.mkdir(parents=True, exist_ok=True)
        replay_filepath = str(replays_dir / f"match_{match_id}.json")
        save_replay(match_result, replay_filepath)

        winner_code = match_result.get("winner")
        result_db = session_factory()
        try:
            match = result_db.query(Match).filter(Match.id == match_id).first()
            player1 = result_db.query(User).filter(User.id == player1_id).first()
            player2 = result_db.query(User).filter(User.id == player2_id).first()
            if match is None or player1 is None or player2 is None:
                logger.error("Match or players disappeared while match %d was running.", match_id)
                return None

            match.replay_path = replay_filepath
            match.win_reason = match_result.get("win_reason")
            match.total_turns = match_result.get("total_turns", 0)
            match.live_moves = json.dumps(match_result.get("moves", []), ensure_ascii=False)
            match.rule_variant = rule_variant
            match.winner_id = player1_id if winner_code == 1 else player2_id if winner_code == 2 else None
            r1, r2 = player1.elo, player2.elo
            match.p1_elo_before, match.p2_elo_before = r1, r2

            if not is_bracket:
                score_1 = 1.0 if winner_code == 1 else 0.0 if winner_code == 2 else 0.5
                delta_1, delta_2 = calculate_elo_delta(r1, r2, score=score_1, multiplier=multiplier_x, k=k_factor)
                player1.elo = apply_elo_change(r1, delta_1)
                player2.elo = apply_elo_change(r2, delta_2)
            match.p1_elo_after, match.p2_elo_after = player1.elo, player2.elo

            if winner_code == 1:
                player1.wins += 1
                player2.losses += 1
            elif winner_code == 2:
                player2.wins += 1
                player1.losses += 1
            else:
                player1.draws += 1
                player2.draws += 1
            result_db.commit()
        finally:
            result_db.close()
        return match_result
    except Exception as exc:
        logger.exception("Error executing match %d: %s", match_id, exc)
        error_db = session_factory()
        try:
            match = error_db.query(Match).filter(Match.id == match_id).first()
            if match:
                match.win_reason = f"Execution error: {exc}"
                error_db.commit()
        except Exception:
            logger.exception("Could not persist failure for match %d", match_id)
        finally:
            error_db.close()
        return None
