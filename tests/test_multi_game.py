"""Tests for multi-game support: grid engines, runner, grader, schema and API."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from engine.games import (
    GAME_CARO,
    GAME_CONNECT4,
    GAME_RPS9,
    SUPPORTED_GAMES,
    CaroGame,
    Connect4Game,
    list_games,
    normalize_game_type,
)
from engine.grader import grade_bot, grade_label
from engine.runner import run_match
from server.database import SessionLocal, engine, init_db
from server.main import app
from server.models import Bot, Match, User
from server.queue import execute_match_job

REPO_ROOT = Path(__file__).resolve().parent.parent
STARTER = REPO_ROOT / "starter_kit"
client = TestClient(app)


# ------------------------------------------------------------------ registry


def test_registry_lists_three_games_easiest_first():
    assert set(SUPPORTED_GAMES) == {GAME_RPS9, GAME_CONNECT4, GAME_CARO}
    assert [g["slug"] for g in list_games()] == [GAME_CONNECT4, GAME_CARO, GAME_RPS9]


def test_normalize_game_type_falls_back_to_default():
    assert normalize_game_type("caro") == GAME_CARO
    assert normalize_game_type(" connect4 ") == GAME_CONNECT4
    assert normalize_game_type("chess") == GAME_RPS9
    assert normalize_game_type(None) == GAME_RPS9


# ------------------------------------------------------------------ connect four


def test_connect4_stones_fall_to_the_bottom():
    game = Connect4Game()
    record = game.apply_move(3)
    assert record["cell"] == [5, 3]
    record = game.apply_move(3)
    assert record["cell"] == [4, 3]
    assert game.board[5][3] == 1 and game.board[4][3] == 2


def test_connect4_vertical_win_and_full_column():
    game = Connect4Game()
    for col in (0, 1, 0, 1, 0, 1, 0):
        game.apply_move(col)
    assert game.winner == 1
    assert game.win_reason == "line"
    assert len(game.winning_line) == 4
    assert game.get_valid_moves() == []

    game = Connect4Game()
    for _ in range(6):
        game.apply_move(6)  # alternating colours, so no vertical four
    assert 6 not in game.get_valid_moves()


def test_connect4_diagonal_win():
    game = Connect4Game()
    # Build a rising diagonal for player 1 at (5,0) (4,1) (3,2) (2,3).
    for col in (0, 1, 1, 2, 2, 3, 2, 3, 3, 6, 3):
        game.apply_move(col)
    assert game.winner == 1


def test_connect4_rejects_malformed_moves():
    game = Connect4Game()
    assert game.normalize_move(True) is None
    assert game.normalize_move("3") is None
    assert game.normalize_move([4]) == 4
    with pytest.raises(ValueError):
        game.apply_move(9)


def test_connect4_draw_on_full_board():
    game = Connect4Game()
    # Column order that fills the board without any four-in-a-row.
    order = [0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0,
             2, 3, 2, 3, 2, 3, 3, 2, 3, 2, 3, 2,
             4, 5, 4, 5, 4, 5, 5, 4, 5, 4, 5, 4,
             6, 6, 6, 6, 6, 6]
    for col in order:
        game.apply_move(col)
    assert game.is_game_over
    assert game.winner is None
    assert game.win_reason == "board_full"


# ------------------------------------------------------------------ caro


def test_caro_five_in_a_row_wins_and_blocks_occupied_cells():
    game = CaroGame()
    for i in range(4):
        game.apply_move((7, 3 + i))
        game.apply_move((0, i))
    assert not game.is_game_over
    with pytest.raises(ValueError):
        game.apply_move((0, 0))
    game.apply_move((7, 7))
    assert game.winner == 1
    assert game.winning_line == [[7, 3], [7, 4], [7, 5], [7, 6], [7, 7]]


def test_caro_normalize_move():
    game = CaroGame()
    assert game.normalize_move([1, 2]) == (1, 2)
    assert game.normalize_move((True, 2)) is None
    assert game.normalize_move(5) is None


# ------------------------------------------------------------------ runner


@pytest.mark.parametrize("game_type, bot", [
    (GAME_CONNECT4, "connect4_bot.py"),
    (GAME_CARO, "caro_bot.py"),
])
def test_runner_plays_grid_games_to_completion(game_type, bot):
    result = run_match(str(STARTER / bot), str(STARTER / bot), game_type=game_type)
    assert result["game_type"] == game_type
    assert result["win_reason"] in ("line", "board_full")
    assert result["total_turns"] == len(result["moves"]) > 0
    assert result["bot1_error"] is None and result["bot2_error"] is None


def test_runner_forfeits_illegal_grid_move(tmp_path):
    bad = tmp_path / "bad_bot.py"
    bad.write_text("def get_move(board, my_player, history):\n    return 99\n", encoding="utf-8")
    result = run_match(str(bad), str(STARTER / "connect4_bot.py"), game_type=GAME_CONNECT4)
    assert result["winner"] == 2
    assert result["win_reason"] == "invalid_move"
    assert "illegal" in result["bot1_error"]


def test_rps_replay_is_tagged_with_its_game():
    result = run_match(str(STARTER / "bot_template.py"), str(STARTER / "heuristic_bot.py"), max_turns=10)
    assert result["game_type"] == GAME_RPS9


# ------------------------------------------------------------------ grader


def test_grader_scores_reference_bot_and_rejects_unsafe_code(tmp_path):
    report = grade_bot(STARTER / "connect4_bot.py", GAME_CONNECT4, games_per_opponent=2)
    assert report["valid"] is True
    assert 0.0 <= report["score"] <= 10.0
    assert [row["name"] for row in report["opponents"]] == ["Random (Lv1)", "Heuristic (Lv2)"]
    assert all(row["wins"] + row["draws"] + row["losses"] == 2 for row in report["opponents"])

    evil = tmp_path / "evil.py"
    evil.write_text("import os\ndef get_move(b, p, h):\n    return 0\n", encoding="utf-8")
    report = grade_bot(evil, GAME_CONNECT4)
    assert report["valid"] is False
    assert report["score"] == 0.0


def test_grade_labels():
    assert grade_label(9.5) == "Xuất sắc"
    assert grade_label(5.0) == "Khá"
    assert grade_label(0.0) == "Cần cố gắng"


# ------------------------------------------------------------------ schema migration


def test_init_db_adds_game_type_to_old_databases(tmp_path):
    old = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with old.begin() as conn:
        conn.execute(text("CREATE TABLE bots (id INTEGER PRIMARY KEY, user_id INTEGER, filename TEXT,"
                          " filepath TEXT, is_active BOOLEAN, uploaded_at DATETIME)"))
        conn.execute(text("INSERT INTO bots (user_id, filename, filepath, is_active) VALUES (1, 'a.py', 'a.py', 1)"))
    init_db(old)
    columns = {c["name"] for c in inspect(old).get_columns("bots")}
    assert "game_type" in columns
    with old.connect() as conn:
        assert conn.execute(text("SELECT game_type FROM bots")).scalar() == "rps9x9"
    old.dispose()


# ------------------------------------------------------------------ API


@pytest.fixture()
def clean_db():
    init_db()
    yield
    engine.dispose()
    for artifact in ["app.db", "app.db-shm", "app.db-wal"]:
        if os.path.exists(artifact):
            try:
                os.remove(artifact)
            except OSError:
                pass
    shutil.rmtree("bots", ignore_errors=True)
    shutil.rmtree("replays", ignore_errors=True)


def _login(username: str) -> tuple[dict, int]:
    client.post("/api/auth/register", json={"username": username, "password": "secret123"})
    res = client.post("/api/auth/login", json={"username": username, "password": "secret123"})
    return {"Authorization": f"Bearer {res.json()['token']}"}, res.json()["user"]["id"]


def _admin_headers() -> dict:
    db = SessionLocal()
    try:
        admin = User(username="mg_admin", is_admin=True)
        admin.set_password("adminpass1")
        db.add(admin)
        db.commit()
    finally:
        db.close()
    res = client.post("/api/auth/login", json={"username": "mg_admin", "password": "adminpass1"})
    return {"Authorization": f"Bearer {res.json()['token']}"}


def _upload(headers: dict, filename: str, game_type: str | None = None):
    source = (STARTER / filename).read_bytes()
    data = {"game_type": game_type} if game_type else {}
    return client.post("/api/bots/upload", headers=headers, data=data,
                       files={"file": (filename, source, "text/x-python")})


def test_one_active_bot_per_game(clean_db):
    headers, _ = _login("multi_alice")
    assert _upload(headers, "heuristic_bot.py").json()["game_type"] == GAME_RPS9
    assert _upload(headers, "connect4_bot.py", GAME_CONNECT4).status_code == 201
    assert _upload(headers, "caro_bot.py", "chess").status_code == 400

    bots = client.get("/api/bots", headers=headers).json()
    active = {b["game_type"] for b in bots if b["is_active"]}
    assert active == {GAME_RPS9, GAME_CONNECT4}

    res = client.get("/api/bots/active", headers=headers, params={"game_type": GAME_CONNECT4})
    assert res.json()["filename"] == "connect4_bot.py"


def test_admin_switches_game_and_challenge_runs_it(clean_db):
    admin = _admin_headers()
    res = client.post("/api/admin/settings", headers=admin,
                      json={"game_type": GAME_CONNECT4, "portal_mode": "true"})
    assert res.status_code == 200
    assert res.json()["game_type"] == GAME_CONNECT4
    assert client.post("/api/admin/settings", headers=admin, json={"game_type": "chess"}).status_code == 400

    alice, _ = _login("mg_alice")
    bob, bob_id = _login("mg_bob")
    _upload(alice, "connect4_bot.py", GAME_CONNECT4)
    _upload(bob, "heuristic_bot.py", GAME_RPS9)

    # Bob has no Connect Four bot yet, so the challenge is refused.
    res = client.post("/api/matches/challenge", headers=alice, json={"opponent_id": bob_id})
    assert res.status_code == 400
    assert "Connect Four" in res.json()["detail"]

    _upload(bob, "connect4_template.py", GAME_CONNECT4)
    res = client.post("/api/matches/challenge", headers=alice, json={"opponent_id": bob_id})
    assert res.status_code == 201
    assert res.json()["game_type"] == GAME_CONNECT4

    db = SessionLocal()
    try:
        match = db.query(Match).filter(Match.id == res.json()["match_id"]).first()
        assert match.game_type == GAME_CONNECT4
        bots = {b.id: b for b in db.query(Bot).all()}
        result = execute_match_job(match.id, bots[match.bot1_id].filepath, bots[match.bot2_id].filepath)
    finally:
        db.close()
    assert result["game_type"] == GAME_CONNECT4
    replay = client.get(f"/api/matches/{res.json()['match_id']}/replay").json()
    assert replay["rows"] == 6 and replay["cols"] == 7
