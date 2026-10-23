"""Tournament administration, setting configuration, and bracket generation routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from engine.game import MAX_TURNS, RULE_VARIANT_CUSTOM, SUPPORTED_RULE_VARIANTS, create_initial_board
from engine.games import GAMES, list_games
from server.boss_manager import deploy_boss, get_all_bosses_status, retract_boss
from server.bracket import (
    STATUS_PENDING,
    STATUS_RUNNING,
    create_bracket,
    get_final_results,
    get_ready_matches,
    is_bracket_finished,
    play_bracket_matches,
    create_qualifier_schedule,
    get_qualifier_standings,
    play_qualifier_batch,
)
from server.database import get_db
from server.games import get_active_bot, get_active_game, get_catalog_games
from server.models import Bot, BracketMatch, Match, QualifierMatch, QualifierTournament, TournamentSetting, User
from server.queue import speed_up_bracket_round
from server.routes.auth import get_current_admin
from server.tournament import generate_bracket, is_ffa_portal_open
from server.tournament_config import load_tournament_config

router = APIRouter(prefix="/admin", tags=["admin"])


class BossDeployRequest(BaseModel):
    """Pydantic payload for deploying or retracting a benchmark boss bot."""
    boss_slug: str
    action: str = "deploy"


class BracketGenerationRequest(BaseModel):
    """Options selected when the organizer creates a bracket tournament."""
    concurrent_boards: int = Field(1, ge=1, le=8)
    participant_ids: Optional[List[int]] = None
    manual_pairs: List[Tuple[Optional[int], Optional[int]]] = Field(default_factory=list)


class QualifierGenerationRequest(BaseModel):
    """Optional explicit entrant list for a qualification stage."""
    participant_ids: Optional[List[int]] = None


class UpdateSettingsRequest(BaseModel):
    """Pydantic payload for updating tournament dynamic parameters."""
    is_portal_open: Optional[Union[bool, str]] = None
    portal_mode: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    daily_multiplier_x: Optional[float] = Field(None, ge=0.1, le=10.0)
    current_day: Optional[int] = Field(None, ge=1)
    total_days: Optional[int] = Field(None, ge=1)
    max_turns: Optional[int] = Field(None, ge=10, le=MAX_TURNS)
    turn_timeout_seconds: Optional[float] = Field(None, ge=0.1, le=10.0)
    rule_variant: Optional[str] = None
    game_type: Optional[str] = None
    catalog_games: Optional[List[str]] = None


def _get_setting_row(db: Session, key: str) -> TournamentSetting | None:
    """Retrieve setting row from database by key."""
    return db.query(TournamentSetting).filter(TournamentSetting.key == key).first()


def _upsert_setting(db: Session, key: str, value: str) -> None:
    """Insert or update a tournament setting key-value pair."""
    setting = _get_setting_row(db, key)
    if setting:
        setting.value = value
    else:
        setting = TournamentSetting(key=key, value=value)
        db.add(setting)


def _get_all_settings_dict(db: Session) -> Dict[str, Any]:
    """Retrieve full configuration merged with database overrides."""
    config = load_tournament_config()
    t_cfg = config.get("tournament", {})
    daily_cfg = t_cfg.get("daily_schedule", {})
    elo_cfg = t_cfg.get("elo", {})
    rules_cfg = t_cfg.get("match_rules", {})
    bracket_cfg = t_cfg.get("final_bracket", {})

    settings_map: Dict[str, str] = {
        s.key: s.value for s in db.query(TournamentSetting).all()
    }
    try:
        concurrent_boards = int(settings_map.get("concurrent_boards", "1"))
    except (TypeError, ValueError):
        concurrent_boards = 1
    concurrent_boards = max(1, min(8, concurrent_boards))

    start_time = settings_map.get("start_time", daily_cfg.get("start_time", "19:00"))
    end_time = settings_map.get("end_time", daily_cfg.get("end_time", "21:00"))
    raw_mode = settings_map.get("portal_mode") or settings_map.get("is_portal_open", "auto")
    raw_mode_str = str(raw_mode).strip().lower()
    if raw_mode_str in ("true", "1", "yes"):
        portal_mode = "true"
    elif raw_mode_str in ("false", "0", "no"):
        portal_mode = "false"
    else:
        portal_mode = "auto"

    # Evaluate dynamic portal state
    portal_open = is_ffa_portal_open(config, db_settings=settings_map)

    # Daily multiplier x
    if "daily_multiplier_x" in settings_map:
        multiplier_x = float(settings_map["daily_multiplier_x"])
    else:
        multiplier_x = float(elo_cfg.get("daily_multiplier_x", 1.5))

    # Current day
    if "current_day" in settings_map:
        current_day = int(settings_map["current_day"])
    else:
        current_day = int(t_cfg.get("current_day", 1))

    # Total days
    if "total_days" in settings_map:
        total_days = int(settings_map["total_days"])
    else:
        total_days = int(t_cfg.get("total_days", 7))

    # Max turns
    if "max_turns" in settings_map:
        max_turns = min(MAX_TURNS, int(settings_map["max_turns"]))
    else:
        max_turns = int(rules_cfg.get("max_turns", MAX_TURNS))
    max_turns = max(10, min(MAX_TURNS, max_turns))

    # Timeout
    if "turn_timeout_seconds" in settings_map:
        timeout_seconds = float(settings_map["turn_timeout_seconds"])
    else:
        timeout_seconds = float(rules_cfg.get("turn_timeout_seconds", 1.0))

    game_type = settings_map.get("game_type", "rps9x9")
    if game_type not in GAMES:
        game_type = "rps9x9"

    return {
        "is_portal_open": portal_open,
        "portal_mode": portal_mode,
        "rule_variant": settings_map.get("rule_variant", "standard"),
        "game_type": game_type,
        "games": list_games(),
        "catalog_games": [game["slug"] for game in get_catalog_games(db)],
        "start_time": start_time,
        "end_time": end_time,
        "daily_multiplier_x": multiplier_x,
        "current_day": current_day,
        "total_days": total_days,
        "max_turns": max_turns,
        "turn_timeout_seconds": timeout_seconds,
        "top_players_count": int(bracket_cfg.get("top_players_count", 8)),
        "concurrent_boards": concurrent_boards,
        "bosses": get_all_bosses_status(db),
    }


@router.get("/settings")
def get_settings(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve active tournament configuration and settings."""
    return _get_all_settings_dict(db)


@router.post("/settings")
def update_settings(
    payload: UpdateSettingsRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Update tournament settings (portal status, schedule, daily multiplier, days limit)."""
    if payload.portal_mode is not None:
        p_mode = payload.portal_mode.strip().lower()
        _upsert_setting(db, "portal_mode", p_mode)
        _upsert_setting(db, "is_portal_open", p_mode)
    elif payload.is_portal_open is not None:
        p_mode = str(payload.is_portal_open).strip().lower()
        _upsert_setting(db, "is_portal_open", p_mode)
        _upsert_setting(db, "portal_mode", p_mode)

    if payload.start_time is not None:
        _upsert_setting(db, "start_time", payload.start_time.strip())

    if payload.end_time is not None:
        _upsert_setting(db, "end_time", payload.end_time.strip())

    if payload.daily_multiplier_x is not None:
        _upsert_setting(db, "daily_multiplier_x", str(payload.daily_multiplier_x))

    if payload.current_day is not None:
        _upsert_setting(db, "current_day", str(payload.current_day))

    if payload.total_days is not None:
        _upsert_setting(db, "total_days", str(payload.total_days))

    if payload.max_turns is not None:
        _upsert_setting(db, "max_turns", str(payload.max_turns))

    if payload.turn_timeout_seconds is not None:
        _upsert_setting(db, "turn_timeout_seconds", str(payload.turn_timeout_seconds))

    if payload.rule_variant is not None:
        candidate_variant = payload.rule_variant.strip()
        if candidate_variant not in SUPPORTED_RULE_VARIANTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported rule variant.",
            )
        if candidate_variant == RULE_VARIANT_CUSTOM:
            try:
                create_initial_board(variant=candidate_variant)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Custom rules are invalid: {exc}",
                ) from exc
        _upsert_setting(db, "rule_variant", candidate_variant)

    if payload.game_type is not None:
        candidate_game = payload.game_type.strip()
        if candidate_game not in GAMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported game type.",
            )
        _upsert_setting(db, "game_type", candidate_game)

    if payload.catalog_games is not None:
        if "rps9x9" not in payload.catalog_games or any(slug not in GAMES for slug in payload.catalog_games):
            raise HTTPException(status_code=400, detail="Catalog must include rps9x9 and supported games only.")
        _upsert_setting(db, "catalog_games", json.dumps(list(dict.fromkeys(payload.catalog_games))))

    db.commit()
    return _get_all_settings_dict(db)


@router.get("/bracket/participants")
def list_bracket_participants(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List non-admin accounts and whether they have a bot for the active game."""
    game_type = get_active_game(db)
    users = db.query(User).filter(User.is_admin.is_(False)).order_by(User.elo.desc(), User.id.asc()).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "elo": user.elo,
            "has_active_bot": get_active_bot(db, user.id, game_type) is not None,
        }
        for user in users
        if get_active_bot(db, user.id, game_type) is not None
    ]


@router.post("/qualifier/generate")
def generate_qualifier_stage(
    payload: QualifierGenerationRequest = QualifierGenerationRequest(),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create and retain a balanced schedule for the selected active bots."""
    active_game = get_active_game(db)
    users = db.query(User).filter(User.is_admin.is_(False)).order_by(User.elo.desc(), User.id.asc()).all()
    users_by_id = {user.id: user for user in users}
    participant_ids = payload.participant_ids
    if participant_ids is None:
        participant_ids = [user.id for user in users if get_active_bot(db, user.id, active_game)]
    if len(set(participant_ids)) != len(participant_ids):
        raise HTTPException(status_code=400, detail="Participant list contains duplicates.")
    if len(participant_ids) < 4:
        raise HTTPException(status_code=400, detail="At least 4 participants are required for qualification games.")
    if set(participant_ids) - users_by_id.keys():
        raise HTTPException(status_code=400, detail="Participants must be existing non-admin accounts.")
    missing_bot = [users_by_id[user_id].username for user_id in participant_ids if not get_active_bot(db, user_id, active_game)]
    if missing_bot:
        raise HTTPException(status_code=400, detail="Every qualification participant must have an active bot for the selected game.")
    if db.query(QualifierMatch).filter(QualifierMatch.status == STATUS_RUNNING).first():
        raise HTTPException(status_code=409, detail="A qualification batch is already running.")
    if db.query(BracketMatch).filter(BracketMatch.status == STATUS_RUNNING).first():
        raise HTTPException(status_code=409, detail="A playoff bracket is currently running.")
    if db.query(BracketMatch).filter(BracketMatch.status == STATUS_PENDING).first():
        raise HTTPException(status_code=409, detail="Finish the current playoff bracket before starting a new qualifier.")
    if db.query(BracketMatch).first():
        raise HTTPException(status_code=409, detail="End the previous tournament before starting a new qualifier so its bracket history can be cleared safely.")
    active_tournament = db.query(QualifierTournament).filter(QualifierTournament.status.in_(("active", "tiebreak"))).first()
    if active_tournament:
        raise HTTPException(status_code=409, detail="Finish the active qualification stage before creating another.")
    variant_row = _get_setting_row(db, "rule_variant")
    variant = variant_row.value if variant_row and variant_row.value else "standard"
    if variant == RULE_VARIANT_CUSTOM:
        try:
            create_initial_board(variant=variant)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Custom rules are invalid: {exc}") from exc

    tournament, pairings = create_qualifier_schedule(db, participant_ids)
    db.commit()
    return {
        "tournament_id": tournament.id,
        "participant_count": tournament.participant_count,
        "rounds": tournament.round_count,
        "games_per_participant": tournament.round_count,
        "matches": sum(not pairing.is_bye for pairing in pairings),
        "byes": sum(pairing.is_bye for pairing in pairings),
        "cutoff": tournament.cutoff,
    }


@router.post("/qualifier/play")
def play_next_qualifier_batch(
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Start the next eight qualification games, or the smaller final batch."""
    tournament = db.query(QualifierTournament).filter(QualifierTournament.status.in_(("active", "tiebreak"))).order_by(QualifierTournament.id.desc()).first()
    if tournament is None:
        raise HTTPException(status_code=400, detail="No active qualification stage exists.")
    if db.query(QualifierMatch).filter(
        QualifierMatch.tournament_id == tournament.id,
        QualifierMatch.status == STATUS_RUNNING,
    ).first():
        raise HTTPException(status_code=409, detail="Wait for the current batch to finish.")
    next_pending = (
        db.query(QualifierMatch)
        .filter(QualifierMatch.tournament_id == tournament.id, QualifierMatch.status == STATUS_PENDING)
        .order_by(QualifierMatch.round_number.asc(), QualifierMatch.batch_number.asc(), QualifierMatch.match_index.asc())
        .first()
    )
    if not next_pending:
        raise HTTPException(status_code=409, detail="All qualification matches are complete; the playoff bracket is being prepared.")
    pending = (
        db.query(QualifierMatch)
        .filter(
            QualifierMatch.tournament_id == tournament.id,
            QualifierMatch.status == STATUS_PENDING,
            QualifierMatch.round_number == next_pending.round_number,
            QualifierMatch.batch_number == next_pending.batch_number,
        )
        .order_by(QualifierMatch.match_index.asc())
        .limit(8)
        .all()
    )

    game_type = get_active_game(db)
    player_ids = {pairing.player1_id for pairing in pending} | {pairing.player2_id for pairing in pending}
    players = {user.id: user for user in db.query(User).filter(User.id.in_(player_ids)).all()}
    variant_row = _get_setting_row(db, "rule_variant")
    variant = variant_row.value if variant_row and variant_row.value else "standard"
    if variant == RULE_VARIANT_CUSTOM:
        try:
            create_initial_board(variant=variant)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Custom rules are invalid: {exc}") from exc
    for pairing in pending:
        bot1 = get_active_bot(db, pairing.player1_id, game_type)
        bot2 = get_active_bot(db, pairing.player2_id, game_type)
        if bot1 is None or bot2 is None:
            raise HTTPException(status_code=400, detail="A qualification participant no longer has an active bot.")
        game = Match(
            player1_id=pairing.player1_id,
            player2_id=pairing.player2_id,
            bot1_id=bot1.id,
            bot2_id=bot2.id,
            p1_elo_before=players[pairing.player1_id].elo,
            p2_elo_before=players[pairing.player2_id].elo,
            is_bracket=True,
            game_type=game_type,
            rule_variant=variant,
        )
        db.add(game)
        db.flush()
        pairing.match_id = game.id
        pairing.status = STATUS_RUNNING
    db.commit()
    match_ids = [pairing.id for pairing in pending]
    round_number = pending[0].round_number
    background_tasks.add_task(play_qualifier_batch, match_ids)
    return {"status": "queued", "round": round_number, "match_count": len(match_ids), "match_ids": match_ids}


@router.post("/bracket/generate")
def trigger_bracket_generation(
    payload: BracketGenerationRequest = BracketGenerationRequest(),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Generate a bracket from selected non-admin participants."""
    if db.query(QualifierTournament).filter(QualifierTournament.status.in_(("active", "tiebreak"))).first():
        raise HTTPException(status_code=409, detail="Complete the qualification and any cutoff playoff before generating a bracket.")
    settings = _get_all_settings_dict(db)
    top_n = settings.get("top_players_count", 8)

    users = db.query(User).filter(User.is_admin.is_(False)).order_by(User.elo.desc(), User.id.asc()).all()
    users_by_id = {user.id: user for user in users}

    if payload.participant_ids is not None:
        if len(set(payload.participant_ids)) != len(payload.participant_ids):
            raise HTTPException(status_code=400, detail="Participant list contains duplicates.")
        unknown_ids = set(payload.participant_ids) - users_by_id.keys()
        if unknown_ids:
            raise HTTPException(status_code=400, detail="Participants must be existing non-admin accounts.")
        selected_users = [users_by_id[user_id] for user_id in payload.participant_ids]
        active_game = get_active_game(db)
        missing_bot = [user.username for user in selected_users if get_active_bot(db, user.id, active_game) is None]
        if missing_bot:
            raise HTTPException(status_code=400, detail="Every participant must have an active bot for the selected game.")
        selected_users.sort(key=lambda user: (-user.elo, user.id))
    else:
        active_game = get_active_game(db)
        selected_users = [user for user in users if get_active_bot(db, user.id, active_game) is not None][:top_n]

    eligible_users = [
        {"id": user.id, "username": user.username, "elo": user.elo}
        for user in selected_users
    ]

    if len(eligible_users) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 participants are required to generate a tournament bracket.",
        )

    if db.query(BracketMatch).filter(BracketMatch.status == STATUS_RUNNING).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bracket matches are currently being played. Wait for them to finish.",
        )

    if payload.manual_pairs:
        participant_ids = {user["id"] for user in eligible_users}
        paired_ids = [player_id for pair in payload.manual_pairs for player_id in pair if player_id is not None]
        if len(paired_ids) != len(set(paired_ids)) or set(paired_ids) != participant_ids:
            raise HTTPException(status_code=400, detail="Manual pairings must include every selected participant exactly once.")
        if any(player1 is None and player2 is None for player1, player2 in payload.manual_pairs):
            raise HTTPException(status_code=400, detail="A manual pairing cannot have two empty slots.")
        if len(eligible_users) < 2:
            raise HTTPException(status_code=400, detail="At least 2 participants are required to generate a tournament bracket.")
        bracket_size = 1 << (len(eligible_users) - 1).bit_length()
        round_name = {2: "Final", 4: "Semi-Final", 8: "Quarter-Final", 16: "Round of 16", 32: "Round of 32", 64: "Round of 64"}.get(bracket_size, f"Round of {bracket_size}")
        users_by_id_payload = {user["id"]: user for user in eligible_users}
        matchups = [
            {
                "match_index": index,
                "round_name": round_name,
                "player1_id": player1,
                "player2_id": player2,
                "player1": users_by_id_payload.get(player1),
                "player2": users_by_id_payload.get(player2),
            }
            for index, (player1, player2) in enumerate(payload.manual_pairs)
        ]
        if len(matchups) != bracket_size // 2:
            raise HTTPException(status_code=400, detail=f"Manual bracket needs {bracket_size // 2} first-round pairings, including byes.")
    else:
        matchups = generate_bracket(eligible_users)

    # Replace the previous bracket with a fresh tree (first round + empty later rounds)
    create_bracket(db, matchups)
    _upsert_setting(db, "concurrent_boards", str(payload.concurrent_boards))
    db.commit()

    return matchups


@router.post("/bracket/play")
def play_next_bracket_round(
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Queue every ready pairing of the earliest unfinished bracket round for execution."""
    all_matches = db.query(BracketMatch).all()
    if not all_matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No bracket has been generated yet.",
        )
    if any(bm.status == STATUS_RUNNING for bm in all_matches):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bracket matches are currently being played. Wait for them to finish.",
        )
    if is_bracket_finished(all_matches):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The bracket is already finished.",
        )

    active_variant = _get_setting_row(db, "rule_variant")
    if active_variant and active_variant.value == RULE_VARIANT_CUSTOM:
        try:
            create_initial_board(variant=RULE_VARIANT_CUSTOM)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Custom rules are invalid; no bracket games were started: {exc}",
            ) from exc

    ready = get_ready_matches(db)
    if not ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No bracket matches are ready to be played.",
        )

    round_name = ready[0].round_name
    match_ids = [bm.id for bm in ready]
    for bm in ready:
        bm.status = STATUS_RUNNING
    db.commit()

    setting = db.query(TournamentSetting).filter(
        TournamentSetting.key == "concurrent_boards"
    ).first()
    try:
        concurrent_boards = max(1, min(8, int(setting.value))) if setting else 1
    except (TypeError, ValueError):
        concurrent_boards = 1
    background_tasks.add_task(play_bracket_matches, match_ids, None, concurrent_boards)

    return {
        "status": "queued",
        "round_name": round_name,
        "bracket_match_ids": match_ids,
        "concurrent_boards": concurrent_boards,
    }


@router.post("/bracket/speed-up", include_in_schema=False)
@router.post("/bracket/finish")
def finish_running_bracket_round(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Skip playback pacing for the currently running qualifier batch or bracket round."""
    qualifier_running = db.query(QualifierMatch).filter(
        QualifierMatch.status == STATUS_RUNNING
    ).first()
    bracket_running = db.query(BracketMatch).filter(
        BracketMatch.status == STATUS_RUNNING
    ).first()
    if not qualifier_running and not bracket_running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is no running qualification batch or bracket round to speed up.",
        )
    speed_up_bracket_round()
    return {"status": "finishing", "stage": "qualifier" if qualifier_running else "bracket"}


@router.post("/tournament/end")
def end_tournament(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Close match submissions and remove stored match and bracket history."""
    if db.query(BracketMatch).filter(BracketMatch.status == STATUS_RUNNING).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Wait for the running bracket round to finish before ending the tournament.",
        )
    replays_dir = Path(__file__).resolve().parents[2] / "replays"
    replay_files = list(replays_dir.glob("match_*.json")) if replays_dir.is_dir() else []
    if db.query(QualifierMatch).filter(QualifierMatch.status == STATUS_RUNNING).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Wait for the running qualification batch to finish before ending the tournament.")
    match_count = db.query(Match).count()
    bracket_count = db.query(BracketMatch).count()
    qualifier_match_count = db.query(QualifierMatch).count()
    qualifier_tournament_count = db.query(QualifierTournament).count()

    db.query(QualifierMatch).delete(synchronize_session=False)
    db.query(QualifierTournament).delete(synchronize_session=False)
    # Match rows point to bracket pairings; clear that FK before deleting either side.
    db.query(Match).update({Match.bracket_match_id: None}, synchronize_session=False)
    db.query(Match).delete(synchronize_session=False)
    db.query(BracketMatch).delete(synchronize_session=False)
    _upsert_setting(db, "portal_mode", "false")
    _upsert_setting(db, "is_portal_open", "false")
    db.commit()

    deleted_replays = 0
    resolved_replays_dir = replays_dir.resolve()
    for replay_file in replay_files:
        try:
            resolved_file = replay_file.resolve()
            if (
                not replay_file.is_symlink()
                and resolved_file.parent == resolved_replays_dir
                and replay_file.name.startswith("match_")
            ):
                resolved_file.unlink()
                deleted_replays += 1
        except OSError:
            continue

    return {
        "status": "ended",
        "deleted_matches": match_count,
        "deleted_bracket_pairings": bracket_count,
        "deleted_qualifier_matches": qualifier_match_count,
        "deleted_qualifier_tournaments": qualifier_tournament_count,
        "deleted_replays": deleted_replays,
        "portal_mode": "false",
    }


@router.get("/bracket/standings")
def get_bracket_standings(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve final tournament placements for actual entrants, without Elo scoring."""
    return get_final_results(db)


@router.get("/bracket")
def get_bracket(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve all current bracket match pairings and statuses."""
    matches = (
        db.query(BracketMatch)
        .order_by(BracketMatch.id.asc())
        .all()
    )
    return [
        {
            "id": bm.id,
            "round_name": bm.round_name,
            "match_index": bm.match_index,
            "player1_id": bm.player1_id,
            "player2_id": bm.player2_id,
            "player1": {"id": bm.player1.id, "username": bm.player1.username} if bm.player1 else None,
            "player2": {"id": bm.player2.id, "username": bm.player2.username} if bm.player2 else None,
            "winner_id": bm.winner_id,
            "score_p1": bm.score_p1,
            "score_p2": bm.score_p2,
            "status": bm.status,
            "created_at": bm.created_at.isoformat() if bm.created_at else None,
        }
        for bm in matches
    ]


@router.get("/bosses")
def list_bosses(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all benchmark boss bots and their current deployment status."""
    return get_all_bosses_status(db)


@router.post("/bosses/deploy")
def toggle_boss_deployment(
    payload: BossDeployRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Deploy or retract a benchmark boss bot in the active tournament arena."""
    action = payload.action.strip().lower()
    if action == "deploy":
        try:
            return deploy_boss(db, payload.boss_slug)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(err),
            )
    elif action == "retract":
        try:
            return retract_boss(db, payload.boss_slug)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(err),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action: '{payload.action}'. Expected 'deploy' or 'retract'.",
        )
