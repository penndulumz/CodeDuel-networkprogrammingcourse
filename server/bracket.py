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
from server.models import Bot, BracketMatch, Match, QualifierMatch, QualifierTournament, TournamentSetting, User
from server.queue import execute_match_job, reset_bracket_speed
from server.tournament import DEFAULT_BRACKET_PLACEMENT_POINTS, ROUND_NAMES
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
_QUALIFIER_LOCK = threading.Lock()


def create_qualifier_schedule(db: Session, participant_ids: list[int]) -> tuple[QualifierTournament, list[QualifierMatch]]:
    """Create a balanced schedule with four games per entrant where possible."""
    if len(participant_ids) < 4:
        raise ValueError("At least 4 participants are required for qualification games.")
    cutoff = 16 if len(participant_ids) >= 16 else 8
    round_count = 4
    tournament = QualifierTournament(
        participant_count=len(participant_ids), cutoff=cutoff, round_count=round_count,
    )
    db.add(tournament)
    db.flush()

    players = list(participant_ids)
    random.shuffle(players)
    # Offsets 1 and 2 form a 4-regular circle graph for fields of at least five.
    edges: set[tuple[int, int]] = set()
    count = len(players)
    for index, player_id in enumerate(players):
        for offset in (1, 2):
            opponent_id = players[(index + offset) % count]
            edges.add(tuple(sorted((player_id, opponent_id))))
    scheduled_edges = sorted(edges)
    if count == 4:
        # Four players have only three distinct opponents; repeat one game per entrant.
        scheduled_edges.extend((tuple(sorted((players[0], players[2]))),
                                tuple(sorted((players[1], players[3])))))

    # Projection batches are fixed at eight scheduled games. A participant can
    # appear on more than one board in a batch; every scheduled pairing still
    # counts as one of that participant's four qualification games.
    schedule = [
        (index // 8 + 1, 1, first, second)
        for index, (first, second) in enumerate(scheduled_edges)
    ]

    created: list[QualifierMatch] = []
    for match_index, (round_number, batch_number, player1_id, player2_id) in enumerate(schedule):
        pairing = QualifierMatch(
            tournament_id=tournament.id,
            round_number=round_number,
            batch_number=batch_number,
            match_index=match_index,
            player1_id=player1_id,
            player2_id=player2_id,
            status=STATUS_PENDING,
        )
        db.add(pairing)
        created.append(pairing)

    db.commit()
    db.refresh(tournament)
    for pairing in created:
        db.refresh(pairing)
    return tournament, created


def get_qualifier_standings(db: Session, tournament_id: int) -> list[dict[str, Any]]:
    """Rank qualification entrants by points, head-to-head, wins, then Elo."""
    pairings = db.query(QualifierMatch).filter(QualifierMatch.tournament_id == tournament_id).all()
    tournament = db.query(QualifierTournament).filter(QualifierTournament.id == tournament_id).first()
    has_playoff = any(item.stage == "playoff" for item in pairings)
    users = {
        user.id: user
        for user in db.query(User).filter(User.is_admin.is_(False)).all()
        if any(user.id in (item.player1_id, item.player2_id) for item in pairings)
    }
    points = {user_id: 0 for user_id in users}
    playoff_points = {user_id: 0 for user_id in users}
    wins = {user_id: 0 for user_id in users}
    played = {user_id: 0 for user_id in users}
    for pairing in pairings:
        if pairing.status != STATUS_COMPLETED:
            continue
        if pairing.is_bye:
            if pairing.stage == "qualifying":
                points[pairing.player1_id] += 1
            continue
        first, second = pairing.player1_id, pairing.player2_id
        if first not in users or second not in users:
            continue
        if pairing.stage == "qualifying":
            played[first] += 1
            played[second] += 1
        elif pairing.stage == "playoff_decider":
            # Extra head-to-head rounds resolve only their two entrants. They
            # must not increase the shared playoff score or reorder qualifiers.
            continue
        point_table = points if pairing.stage == "qualifying" else playoff_points
        if pairing.winner_id == first:
            point_table[first] += 3
            if pairing.stage == "qualifying":
                wins[first] += 1
        elif pairing.winner_id == second:
            point_table[second] += 3
            if pairing.stage == "qualifying":
                wins[second] += 1
        else:
            point_table[first] += 1
            point_table[second] += 1

    rows = []
    for user_id, user in users.items():
        rows.append({
            "id": user_id,
            "username": user.username,
            "elo": user.elo,
            "points": points[user_id],
            "playoff_points": playoff_points[user_id],
            "wins": wins[user_id],
            "played": played[user_id],
        })

    # Resolve tied point groups by their mini-table before final seeds.
    rows.sort(key=lambda row: (
        -row["points"],
        -row["playoff_points"] if has_playoff else 0,
    ))
    ordered: list[dict[str, Any]] = []
    index = 0
    while index < len(rows):
        group_key = rows[index]["points"]
        tied = []
        while index < len(rows) and rows[index]["points"] == group_key:
            tied.append(rows[index])
            index += 1
        tied_ids = {row["id"] for row in tied}
        mini_points = {user_id: 0 for user_id in tied_ids}
        for pairing in pairings:
            if (pairing.status != STATUS_COMPLETED or pairing.is_bye or pairing.stage != "qualifying"
                    or pairing.player1_id not in tied_ids or pairing.player2_id not in tied_ids):
                continue
            if pairing.winner_id in mini_points:
                mini_points[pairing.winner_id] += 3
            else:
                mini_points[pairing.player1_id] += 1
                mini_points[pairing.player2_id] += 1
        for row in tied:
            row["head_to_head"] = mini_points[row["id"]]
        ordered.extend(sorted(tied, key=lambda row: (
            -row["playoff_points"], -row["head_to_head"], -row["wins"], -row["elo"], row["id"],
        )))
    return ordered


def _finalize_qualifier_bracket(db: Session, tournament_id: int) -> bool:
    """Create the seeded playoff bracket once every qualification pairing is done."""
    pairings = db.query(QualifierMatch).filter(QualifierMatch.tournament_id == tournament_id).all()
    if not pairings or any(item.status != STATUS_COMPLETED for item in pairings):
        return False
    tournament = db.query(QualifierTournament).filter(QualifierTournament.id == tournament_id).first()
    if tournament is None:
        return False
    if tournament.status == "completed":
        return True
    standings = get_qualifier_standings(db, tournament_id)
    if len(standings) < 2:
        return False
    tie_matches = [item for item in pairings if item.stage in ("playoff", "playoff_decider")]
    if tournament.status == "active" and not tie_matches:
        boundary_points = standings[min(tournament.cutoff, len(standings)) - 1]["points"]
        above_boundary = sum(row["points"] > boundary_points for row in standings)
        tied_at_boundary = [row for row in standings if row["points"] == boundary_points]
        if above_boundary < tournament.cutoff < above_boundary + len(tied_at_boundary):
            entrants = [row["id"] for row in tied_at_boundary]
            edges: list[tuple[int, int]] = []
            if len(entrants) <= 12:
                edges = [(entrants[i], entrants[j]) for i in range(len(entrants)) for j in range(i + 1, len(entrants))]
            else:
                # Keep large tie playoffs bounded while giving everyone distinct opponents.
                players = list(entrants)
                random.shuffle(players)
                edge_set = set()
                for index, player_id in enumerate(players):
                    for offset in (1, 2):
                        edge_set.add(tuple(sorted((player_id, players[(index + offset) % len(players)]))))
                if len(players) % 2 == 0:
                    half = len(players) // 2
                    for index in range(half):
                        edge_set.add(tuple(sorted((players[index], players[index + half]))))
                edges = sorted(edge_set)
            last_qualifying_batch = max(item.round_number for item in pairings if item.stage == "qualifying")
            for batch_index, batch_start in enumerate(range(0, len(edges), 8), start=1):
                round_number = last_qualifying_batch + batch_index
                for match_index, (first, second) in enumerate(edges[batch_start:batch_start + 8]):
                    db.add(QualifierMatch(
                        tournament_id=tournament_id,
                        round_number=round_number,
                        batch_number=1,
                        match_index=match_index,
                        stage="playoff",
                        player1_id=first,
                        player2_id=second,
                        status=STATUS_PENDING,
                    ))
            tournament.status = "tiebreak"
            db.commit()
            return False

    if tournament.status == "tiebreak" and tie_matches:
        # If the cutoff is still tied after a playoff, schedule a direct
        # decider. Decider rounds do not add playoff points, so their winner
        # cannot overtake entrants whose positions were already settled.
        boundary = standings[min(tournament.cutoff, len(standings)) - 1]
        boundary_key = (boundary["points"], boundary["playoff_points"])
        tied_at_boundary = [
            row for row in standings
            if (row["points"], row["playoff_points"]) == boundary_key
        ]
        above_boundary = sum(
            (row["points"], row["playoff_points"]) > boundary_key
            for row in standings
        )
        if above_boundary < tournament.cutoff < above_boundary + len(tied_at_boundary) \
                and len(tied_at_boundary) == 2:
            tied_ids = {row["id"] for row in tied_at_boundary}
            deciders = [
                item for item in pairings
                if item.stage == "playoff_decider"
                and {item.player1_id, item.player2_id} == tied_ids
            ]
            latest_decider = max(deciders, key=lambda item: item.round_number, default=None)
            if latest_decider is not None and latest_decider.winner_id in tied_ids:
                winner_index = next(i for i, row in enumerate(standings)
                                    if row["id"] == latest_decider.winner_id)
                loser_id = next(iter(tied_ids - {latest_decider.winner_id}))
                loser_index = next(i for i, row in enumerate(standings) if row["id"] == loser_id)
                if winner_index > loser_index:
                    standings[winner_index], standings[loser_index] = standings[loser_index], standings[winner_index]
            else:
                next_round = max(item.round_number for item in pairings) + 1
                db.add(QualifierMatch(
                    tournament_id=tournament_id,
                    round_number=next_round,
                    batch_number=1,
                    match_index=0,
                    stage="playoff_decider",
                    player1_id=tied_at_boundary[0]["id"],
                    player2_id=tied_at_boundary[1]["id"],
                    status=STATUS_PENDING,
                ))
                db.commit()
                return False

    selected = standings[:tournament.cutoff]
    size = tournament.cutoff
    first_round_name = get_round_name(size)
    from server.tournament import _get_bracket_seed_pairs
    matchups = []
    for index, (seed1, seed2) in enumerate(_get_bracket_seed_pairs(size)):
        first = selected[seed1 - 1] if seed1 <= len(selected) else None
        second = selected[seed2 - 1] if seed2 <= len(selected) else None
        matchups.append({
            "round_name": first_round_name,
            "match_index": index,
            "player1_id": first["id"] if first else None,
            "player2_id": second["id"] if second else None,
        })
    create_bracket(db, matchups)
    tournament.status = "completed"
    db.commit()
    return True


def play_qualifier_match(
    qualifier_match_id: int,
    db_factory: Callable[[], Any] | None = None,
) -> None:
    """Run one prepared qualification game and persist its result."""
    session_factory = db_factory or SessionLocal
    db = session_factory()
    try:
        pairing = db.query(QualifierMatch).filter(QualifierMatch.id == qualifier_match_id).first()
        if pairing is None or pairing.status != STATUS_RUNNING or pairing.match_id is None:
            return
        match = db.query(Match).filter(Match.id == pairing.match_id).first()
        if match is None:
            pairing.status = STATUS_PENDING
            db.commit()
            return
        bot1, bot2 = match.bot1, match.bot2
        if bot1 is None or bot2 is None:
            pairing.status = STATUS_PENDING
            db.commit()
            return
        match_id, path1, path2 = match.id, bot1.filepath, bot2.filepath
    finally:
        db.close()

    result = execute_match_job(match_id, path1, path2, db_factory=session_factory)
    db = session_factory()
    try:
        pairing = db.query(QualifierMatch).filter(QualifierMatch.id == qualifier_match_id).first()
        if pairing is None:
            return
        tournament_id = pairing.tournament_id
        if result is None:
            pairing.status = STATUS_PENDING
        else:
            match = db.query(Match).filter(Match.id == match_id).first()
            pairing.winner_id = match.winner_id if match else None
            pairing.status = STATUS_COMPLETED
        db.commit()
        with _QUALIFIER_LOCK:
            _finalize_qualifier_bracket(db, tournament_id)
    finally:
        db.close()


def play_qualifier_batch(
    qualifier_match_ids: list[int],
    db_factory: Callable[[], Any] | None = None,
) -> None:
    """Run one visible batch of up to eight independent qualification games."""
    try:
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(qualifier_match_ids)))) as executor:
            futures = [executor.submit(play_qualifier_match, item, db_factory) for item in qualifier_match_ids]
            for future in futures:
                future.result()
    finally:
        reset_bracket_speed()


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
    """Rank only this tournament's entrants by bracket and qualification results.

    Args:
        db: Active database session.

    Returns:
        Tournament-only result rows with no Elo fields, or an empty list while
        no bracket placement is available.
    """
    matches = db.query(BracketMatch).all()
    standings = compute_bracket_standings(matches)
    if not standings:
        return []

    qualifier = db.query(QualifierTournament).order_by(QualifierTournament.id.desc()).first()
    qualifier_rows: list[dict[str, Any]] = []
    participant_ids = set(standings)
    if qualifier is not None:
        qualifier_matches = db.query(QualifierMatch).filter(
            QualifierMatch.tournament_id == qualifier.id
        ).all()
        participant_ids.update(
            player_id
            for pairing in qualifier_matches
            for player_id in (pairing.player1_id, pairing.player2_id)
            if player_id is not None
        )
        qualifier_rows = get_qualifier_standings(db, qualifier.id)

    users = db.query(User).filter(
        User.is_admin.is_(False), User.id.in_(participant_ids)
    ).all()
    users_by_id = {user.id: user for user in users}
    qualifier_order = sorted(qualifier_rows, key=lambda row: (
        -row["points"], -row["playoff_points"], -row["head_to_head"],
        -row["wins"], row["id"],
    ))
    non_bracket_ids = [row["id"] for row in qualifier_order if row["id"] not in standings]
    non_bracket_rank = {
        user_id: (qualifier.cutoff if qualifier else len(standings)) + index
        for index, user_id in enumerate(non_bracket_ids, start=1)
    }

    results = []
    for user_id, user in users_by_id.items():
        bracket_rank = standings.get(user_id)
        rank = bracket_rank if bracket_rank is not None else non_bracket_rank.get(user_id)
        if rank is None:
            continue
        results.append({
            "id": user_id,
            "username": user.username,
            "rank": rank,
            "bracket_rank": bracket_rank,
            "result_label": f"Bracket · hạng {bracket_rank}" if bracket_rank is not None else "Vòng loại",
            "bracket_score": DEFAULT_BRACKET_PLACEMENT_POINTS.get(bracket_rank, 0.0),
            "final_score": DEFAULT_BRACKET_PLACEMENT_POINTS.get(bracket_rank, 0.0),
        })
    results.sort(key=lambda item: (item["rank"], item["id"]))
    return results
