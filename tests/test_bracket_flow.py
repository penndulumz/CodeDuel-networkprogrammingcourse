"""Tests for the playoff bracket lifecycle: tree creation, series play, random draw, standings."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from server.bracket import (
    ROUND_ORDER,
    STATUS_COMPLETED,
    STATUS_PENDING,
    compute_bracket_standings,
    create_bracket,
    get_final_results,
    get_ready_matches,
    is_bracket_finished,
    parse_best_of,
    play_bracket_matches,
    play_bracket_series,
)
from server.database import init_db
from server.models import Bot, BracketMatch, Match, User
from server.tournament import generate_bracket

STARTER_KIT = Path(__file__).resolve().parent.parent / "starter_kit"
STRONG_BOT = str(STARTER_KIT / "heuristic_bot.py")
CRASH_BOT_SOURCE = "def get_move(board, my_player, history):\n    raise ValueError('boom')\n"


@pytest.fixture
def session_factory(tmp_path, monkeypatch):
    """Provide an isolated SQLite database and working directory for replay output."""
    monkeypatch.chdir(tmp_path)
    test_engine = create_engine(f"sqlite:///{tmp_path / 'bracket.db'}")
    init_db(test_engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    yield factory
    test_engine.dispose()


def _seed_players(factory, tmp_path, count, strong_ids=()):
    """Create players with descending Elo; seeds listed in strong_ids get a working bot."""
    crash_bot = tmp_path / "crash_bot.py"
    crash_bot.write_text(CRASH_BOT_SOURCE, encoding="utf-8")

    db = factory()
    try:
        users = []
        for i in range(count):
            user = User(username=f"seed_{i + 1}", elo=2000 - i * 100)
            user.set_password("password123")
            db.add(user)
            db.flush()
            path = STRONG_BOT if (i + 1) in strong_ids else str(crash_bot)
            db.add(Bot(user_id=user.id, filename="bot.py", filepath=path, is_active=True))
            users.append({"id": user.id, "username": user.username, "elo": user.elo})
        db.commit()
        return users
    finally:
        db.close()


def test_parse_best_of():
    """Verify series format parsing and fallbacks."""
    assert parse_best_of("BO1") == 1
    assert parse_best_of("bo3") == 3
    assert parse_best_of("BO5") == 5
    assert parse_best_of("BO4") == 5
    assert parse_best_of(None) == 3
    assert parse_best_of("garbage") == 3


def test_round_names_match_generated_bracket():
    """Round labels shown on the bracket page must be the ones generate_bracket emits."""
    for size in (2, 4, 8, 16):
        users = [{"id": i, "elo": 2000 - i} for i in range(1, size + 1)]
        assert generate_bracket(users)[0]["round_name"] in ROUND_ORDER


def test_create_bracket_builds_full_tree(session_factory, tmp_path):
    """An 8-player bracket stores 4 quarter-finals, 2 semi-finals, and the final."""
    users = _seed_players(session_factory, tmp_path, 8)
    db = session_factory()
    try:
        created = create_bracket(db, generate_bracket(users))
        assert [bm.round_name for bm in created] == (
            ["Quarter-Final"] * 4 + ["Semi-Final"] * 2 + ["Final"]
        )
        assert all(bm.status == STATUS_PENDING for bm in created)
        assert all(bm.player1_id and bm.player2_id for bm in created[:4])
        assert all(bm.player1_id is None and bm.player2_id is None for bm in created[4:])

        # Only the seeded first round is ready to be played
        assert [bm.id for bm in get_ready_matches(db)] == [bm.id for bm in created[:4]]

        # Regenerating replaces the whole tree instead of piling up rows
        create_bracket(db, generate_bracket(users))
        assert db.query(BracketMatch).count() == 7
    finally:
        db.close()


def test_series_result_and_skips_elo(session_factory, tmp_path):
    """A BO3 series is decided 2-0, Elo is untouched, and no draw happens mid-round."""
    users = _seed_players(session_factory, tmp_path, 4, strong_ids=(4,))
    db = session_factory()
    try:
        created = create_bracket(db, generate_bracket(users))
        semi_1v4 = created[0]
        assert {semi_1v4.player1_id, semi_1v4.player2_id} == {users[0]["id"], users[3]["id"]}
        semi_id, final_id = semi_1v4.id, created[2].id
    finally:
        db.close()

    winner_id = play_bracket_series(semi_id, db_factory=session_factory)
    assert winner_id == users[3]["id"]

    db = session_factory()
    try:
        semi = db.query(BracketMatch).filter(BracketMatch.id == semi_id).one()
        assert semi.status == STATUS_COMPLETED
        assert semi.winner_id == users[3]["id"]
        assert (semi.score_p1, semi.score_p2) == (0, 2)

        # The other semi-final is still pending, so the final is not drawn yet
        final = db.query(BracketMatch).filter(BracketMatch.id == final_id).one()
        assert final.player1_id is None
        assert final.player2_id is None

        games = db.query(Match).order_by(Match.id.asc()).all()
        assert len(games) == 2
        assert all(g.is_bracket for g in games)
        # Sides alternate between games
        assert games[0].player1_id == games[1].player2_id

        assert db.query(User).filter(User.id == users[0]["id"]).one().elo == users[0]["elo"]
        assert db.query(User).filter(User.id == users[3]["id"]).one().elo == users[3]["elo"]
    finally:
        db.close()


def test_missing_bot_forfeits_series(session_factory, tmp_path):
    """A player without an active bot loses the series without any game being played."""
    users = _seed_players(session_factory, tmp_path, 2, strong_ids=(1, 2))
    db = session_factory()
    try:
        db.query(Bot).filter(Bot.user_id == users[0]["id"]).update({"is_active": False})
        final_id = create_bracket(db, generate_bracket(users))[0].id
    finally:
        db.close()

    assert play_bracket_series(final_id, db_factory=session_factory) == users[1]["id"]

    db = session_factory()
    try:
        assert db.query(Match).count() == 0
    finally:
        db.close()


def test_next_round_is_random_draw_of_winners(session_factory, tmp_path, monkeypatch):
    """After a round finishes, losers are out and winners are shuffled into the next round."""
    users = _seed_players(session_factory, tmp_path, 8)
    shuffle_calls = []

    def fake_shuffle(items):
        shuffle_calls.append(list(items))
        items.reverse()

    monkeypatch.setattr("server.bracket.random.shuffle", fake_shuffle)

    db = session_factory()
    try:
        # Nobody has an active bot, so every series goes to the better seed without games
        db.query(Bot).update({"is_active": False})
        create_bracket(db, generate_bracket(users))
        ready_ids = [bm.id for bm in get_ready_matches(db)]
    finally:
        db.close()

    # Quarter-finals are (1v8), (4v5), (2v7), (3v6): seeds 1, 4, 2, 3 go through
    play_bracket_matches(ready_ids[:3], db_factory=session_factory)
    assert shuffle_calls == []

    play_bracket_matches(ready_ids[3:], db_factory=session_factory)
    winners = [users[0]["id"], users[3]["id"], users[1]["id"], users[2]["id"]]
    assert shuffle_calls == [winners]

    db = session_factory()
    try:
        semis = (
            db.query(BracketMatch)
            .filter(BracketMatch.round_name == "Semi-Final")
            .order_by(BracketMatch.match_index.asc())
            .all()
        )
        drawn = [pid for bm in semis for pid in (bm.player1_id, bm.player2_id)]
        assert drawn == list(reversed(winners))

        eliminated = {users[i]["id"] for i in (4, 5, 6, 7)}
        assert eliminated.isdisjoint(drawn)
        assert len(get_ready_matches(db)) == 2

        final = db.query(BracketMatch).filter(BracketMatch.round_name == "Final").one()
        assert final.player1_id is None and final.player2_id is None
    finally:
        db.close()


def test_full_bracket_run_and_final_results(session_factory, tmp_path):
    """Play a 4-player bracket to the end and verify standings and composite scores."""
    users = _seed_players(session_factory, tmp_path, 4, strong_ids=(3,))

    db = session_factory()
    try:
        # Seed 4 has no active bot, so seed 1 advances by forfeit
        db.query(Bot).filter(Bot.user_id == users[3]["id"]).update({"is_active": False})
        create_bracket(db, generate_bracket(users))
        ready_ids = [bm.id for bm in get_ready_matches(db)]
        assert len(ready_ids) == 2
    finally:
        db.close()
    play_bracket_matches(ready_ids, db_factory=session_factory)

    db = session_factory()
    try:
        assert not is_bracket_finished(db.query(BracketMatch).all())
        ready_ids = [bm.id for bm in get_ready_matches(db)]
        assert len(ready_ids) == 1
    finally:
        db.close()
    play_bracket_matches(ready_ids, db_factory=session_factory)

    db = session_factory()
    try:
        matches = db.query(BracketMatch).all()
        assert is_bracket_finished(matches)
        assert get_ready_matches(db) == []

        # Seed 3 has the only working bot and beats seed 2, then seed 1 in the final
        standings = compute_bracket_standings(matches)
        assert standings == {
            users[2]["id"]: 1,
            users[0]["id"]: 2,
            users[1]["id"]: 3,
            users[3]["id"]: 3,
        }

        results = get_final_results(db)
        by_id = {r["id"]: r for r in results}
        assert by_id[users[2]["id"]]["bracket_score"] == 100.0
        assert by_id[users[0]["id"]]["bracket_score"] == 80.0
        assert by_id[users[1]["id"]]["bracket_score"] == 60.0
        # Seed 1: 0.5 * 100 (top Elo) + 0.5 * 80 (runner-up)
        assert by_id[users[0]["id"]]["final_score"] == pytest.approx(90.0)
        assert [r["rank"] for r in results] == [1, 2, 3, 4]
    finally:
        db.close()
