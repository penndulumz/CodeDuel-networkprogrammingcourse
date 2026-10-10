"""Tests for rating history reconstruction service and Top Teams trajectory."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.database import Base
from server.models import Match, User
from server.rating_history import (
    PALETTE,
    get_top_teams_rating_history,
    get_user_rating_history,
)


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_get_user_rating_history_nonexistent_user(db_session):
    """Verify that querying a non-existent user returns None."""
    result = get_user_rating_history(user_id=99999, db=db_session)
    assert result is None


def test_get_user_rating_history_zero_matches(db_session):
    """Verify user with 0 completed matches returns an initial 1200 milestone."""
    user = User(username="alice", elo=1200)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    result = get_user_rating_history(user_id=user.id, db=db_session)
    assert result is not None
    assert result["user_id"] == user.id
    assert result["username"] == "alice"
    assert result["current_elo"] == 1200
    assert result["peak_elo"] == 1200
    assert result["lowest_elo"] == 1200
    assert result["total_matches"] == 0

    points = result["points"]
    assert len(points) == 1
    start_point = points[0]
    assert start_point["match_id"] == 0
    assert start_point["elo"] == 1200
    assert start_point["delta"] == 0
    assert start_point["opponent"] == "Start"
    assert start_point["win"] is None
    assert isinstance(start_point["created_at"], str)


def test_get_user_rating_history_multiple_matches_chronological(db_session):
    """Verify chronological sequence, opponent labels, wins, and Elo deltas."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=5)
    alice = User(username="alice", elo=1212, created_at=base_time - timedelta(hours=1))
    bob = User(username="bob", elo=1168, created_at=base_time - timedelta(hours=1))
    charlie = User(username="charlie", elo=1220, created_at=base_time - timedelta(hours=1))
    db_session.add_all([alice, bob, charlie])
    db_session.commit()

    # Match 1: Alice (p1) vs Bob (p2) -> Alice wins (+32)
    m1 = Match(
        player1_id=alice.id,
        player2_id=bob.id,
        winner_id=alice.id,
        win_reason="goal",
        p1_elo_before=1200,
        p1_elo_after=1232,
        p2_elo_before=1200,
        p2_elo_after=1168,
        is_bracket=False,
        created_at=base_time + timedelta(hours=1),
    )
    # Match 2: Charlie (p1) vs Alice (p2) -> Charlie wins, Alice loses (-20)
    m2 = Match(
        player1_id=charlie.id,
        player2_id=alice.id,
        winner_id=charlie.id,
        win_reason="elimination",
        p1_elo_before=1200,
        p1_elo_after=1220,
        p2_elo_before=1232,
        p2_elo_after=1212,
        is_bracket=False,
        created_at=base_time + timedelta(hours=2),
    )
    # Match 3: Alice (p1) vs Charlie (p2) -> Draw (delta 0)
    m3 = Match(
        player1_id=alice.id,
        player2_id=charlie.id,
        winner_id=None,
        win_reason="max_turns_draw",
        p1_elo_before=1212,
        p1_elo_after=1212,
        p2_elo_before=1220,
        p2_elo_after=1220,
        is_bracket=False,
        created_at=base_time + timedelta(hours=3),
    )
    db_session.add_all([m1, m2, m3])
    db_session.commit()

    result = get_user_rating_history(user_id=alice.id, db=db_session)
    assert result is not None
    assert result["user_id"] == alice.id
    assert result["username"] == "alice"
    assert result["current_elo"] == 1212
    assert result["peak_elo"] == 1232
    assert result["lowest_elo"] == 1200
    assert result["total_matches"] == 3

    points = result["points"]
    assert len(points) == 4

    # Initial milestone
    assert points[0]["match_id"] == 0
    assert points[0]["elo"] == 1200
    assert points[0]["delta"] == 0
    assert points[0]["opponent"] == "Start"
    assert points[0]["win"] is None

    # Match 1 milestone
    assert points[1]["match_id"] == m1.id
    assert points[1]["elo"] == 1232
    assert points[1]["delta"] == 32
    assert points[1]["opponent"] == "bob"
    assert points[1]["win"] is True

    # Match 2 milestone
    assert points[2]["match_id"] == m2.id
    assert points[2]["elo"] == 1212
    assert points[2]["delta"] == -20
    assert points[2]["opponent"] == "charlie"
    assert points[2]["win"] is False

    # Match 3 milestone (draw)
    assert points[3]["match_id"] == m3.id
    assert points[3]["elo"] == 1212
    assert points[3]["delta"] == 0
    assert points[3]["opponent"] == "charlie"
    assert points[3]["win"] is None


def test_get_user_rating_history_excludes_bracket_and_pending(db_session):
    """Verify that playoff bracket matches and uncompleted matches are ignored."""
    base_time = datetime.now(timezone.utc)
    u1 = User(username="u1", elo=1300)
    u2 = User(username="u2", elo=1200)
    db_session.add_all([u1, u2])
    db_session.commit()

    # Completed regular match
    m_reg = Match(
        player1_id=u1.id,
        player2_id=u2.id,
        winner_id=u1.id,
        win_reason="goal",
        p1_elo_before=1200,
        p1_elo_after=1300,
        p2_elo_before=1200,
        p2_elo_after=1100,
        is_bracket=False,
        created_at=base_time,
    )
    # Bracket match (should be excluded)
    m_bracket = Match(
        player1_id=u1.id,
        player2_id=u2.id,
        winner_id=u1.id,
        win_reason="goal",
        p1_elo_before=1300,
        p1_elo_after=1350,
        p2_elo_before=1100,
        p2_elo_after=1050,
        is_bracket=True,
        created_at=base_time + timedelta(minutes=10),
    )
    # Incomplete pending match (no winner, no win_reason)
    m_pending = Match(
        player1_id=u1.id,
        player2_id=u2.id,
        winner_id=None,
        win_reason=None,
        p1_elo_before=1300,
        p1_elo_after=None,
        p2_elo_before=1100,
        p2_elo_after=None,
        is_bracket=False,
        created_at=base_time + timedelta(minutes=20),
    )
    db_session.add_all([m_reg, m_bracket, m_pending])
    db_session.commit()

    res1 = get_user_rating_history(user_id=u1.id, db=db_session)
    assert res1["total_matches"] == 1
    assert len(res1["points"]) == 2
    assert res1["points"][1]["match_id"] == m_reg.id


def test_get_user_rating_history_limit_and_clamping(db_session):
    """Verify limit slicing and boundary clamping between 5 and 100."""
    user = User(username="grinder", elo=1400)
    dummy = User(username="dummy", elo=1200)
    db_session.add_all([user, dummy])
    db_session.commit()

    # Create 8 matches
    base_time = datetime.now(timezone.utc) - timedelta(hours=10)
    for i in range(8):
        m = Match(
            player1_id=user.id,
            player2_id=dummy.id,
            winner_id=user.id,
            win_reason="goal",
            p1_elo_before=1200 + i * 20,
            p1_elo_after=1200 + (i + 1) * 20,
            p2_elo_before=1200 - i * 20,
            p2_elo_after=1200 - (i + 1) * 20,
            is_bracket=False,
            created_at=base_time + timedelta(hours=i),
        )
        db_session.add(m)
    db_session.commit()

    # Request with limit=5 -> returns 1 initial point + 5 latest match points
    res = get_user_rating_history(user_id=user.id, db=db_session, limit=5)
    assert res["total_matches"] == 8
    # 1 initial + 5 sliced matches
    assert len(res["points"]) == 6
    assert res["points"][0]["match_id"] == 0

    # Request with limit=1 -> clamped to minimum 5
    res_clamped_low = get_user_rating_history(user_id=user.id, db=db_session, limit=1)
    assert len(res_clamped_low["points"]) == 6

    # Request with limit=50 -> returns all 8 matches + 1 initial
    res_large = get_user_rating_history(user_id=user.id, db=db_session, limit=50)
    assert len(res_large["points"]) == 9


def test_get_top_teams_rating_history_empty_db(db_session):
    """Verify empty database returns empty user list without error."""
    result = get_top_teams_rating_history(db=db_session)
    assert result == {"users": []}


def test_get_top_teams_rating_history_ranking_and_palette(db_session):
    """Verify top N users are ranked by Elo desc and assigned distinct palette colors."""
    users = []
    base_elo = 1200
    for i in range(7):
        u = User(username=f"team_{i}", elo=base_elo + i * 50)
        users.append(u)
    db_session.add_all(users)
    db_session.commit()

    # Request top 3 teams
    result = get_top_teams_rating_history(db=db_session, top=3, limit=10)
    top_list = result["users"]
    assert len(top_list) == 3

    # Ranks must be 1, 2, 3 ordered by elo descending
    assert top_list[0]["username"] == "team_6"
    assert top_list[0]["rank"] == 1
    assert top_list[0]["current_elo"] == 1500
    assert top_list[0]["color"] == PALETTE[0]

    assert top_list[1]["username"] == "team_5"
    assert top_list[1]["rank"] == 2
    assert top_list[1]["current_elo"] == 1450
    assert top_list[1]["color"] == PALETTE[1]

    assert top_list[2]["username"] == "team_4"
    assert top_list[2]["rank"] == 3
    assert top_list[2]["current_elo"] == 1400
    assert top_list[2]["color"] == PALETTE[2]

    # Verify clamping: top=0 clamped to 1
    res_clamp_min = get_top_teams_rating_history(db=db_session, top=0)
    assert len(res_clamp_min["users"]) == 1

    # Verify clamping: top=20 clamped to 10 (or total available users, which is 7)
    res_clamp_max = get_top_teams_rating_history(db=db_session, top=20)
    assert len(res_clamp_max["users"]) == 7
