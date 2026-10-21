"""Integration verification tests for merged feature branches:
- live tournament projections + custom rules
- multi-game arena UI + clubhouse redesign
- WAN deployment configs
"""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from engine.games import GAME_RPS9
from engine.runner import run_match
from server.database import init_db
from server.main import app


def test_merge_integration_run_match_with_custom_and_callback():
    """Verify runner handles moves and progress callbacks without error."""
    recorded_progress = []

    def on_progress(moves):
        recorded_progress.append(len(moves))

    # Standard rps bot paths from starter_kit
    b1 = "starter_kit/bot_template.py"
    b2 = "starter_kit/heuristic_bot.py"

    res = run_match(
        bot1_path=b1,
        bot2_path=b2,
        max_turns=6,
        timeout_per_turn=1.0,
        variant="standard",
        game_type=GAME_RPS9,
        progress_callback=on_progress,
    )
    assert res["game_type"] == GAME_RPS9
    assert res["rule_variant"] == "standard"
    assert "goals" in res
    assert "tiebreak_scores" in res
    assert len(recorded_progress) > 0


def test_merge_integration_schema_upgrade_idempotence():
    """Verify init_db initializes all columns (live_moves, bracket_match_id, game_type, game_results)."""
    test_engine = create_engine("sqlite:///:memory:")
    init_db(test_engine)

    # Calling init_db again must be completely idempotent
    init_db(test_engine)

    from sqlalchemy import inspect
    inspector = inspect(test_engine)
    match_cols = {c["name"] for c in inspector.get_columns("matches")}
    assert "bracket_match_id" in match_cols
    assert "live_moves" in match_cols
    assert "game_type" in match_cols

    bracket_cols = {c["name"] for c in inspector.get_columns("bracket_matches")}
    assert "game_results" in bracket_cols

    bot_cols = {c["name"] for c in inspector.get_columns("bots")}
    assert "game_type" in bot_cols


def test_merge_integration_bracket_live_and_games_routes():
    """Verify both /api/bracket/live and /games coexist cleanly."""
    init_db()
    client = TestClient(app)

    # Public bracket projection endpoint
    res_bracket = client.get("/api/bracket/live")
    assert res_bracket.status_code == 200
    data = res_bracket.json()
    assert "pairings" in data

    # Public games page
    res_games = client.get("/games")
    assert res_games.status_code == 200

    # Public home page
    res_home = client.get("/")
    assert res_home.status_code == 200
