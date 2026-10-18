"""Tests for the public website pages, offline kit, grading API and WAN helpers."""

from __future__ import annotations

import io
import os
import shutil
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import parse_tunnel_url
from server.database import SessionLocal, engine, init_db
from server.main import app
from server.models import User

STARTER = Path(__file__).resolve().parent.parent / "starter_kit"


@pytest.fixture(autouse=True)
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


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _login(client: TestClient, username: str) -> dict:
    client.post("/api/auth/register", json={"username": username, "password": "secret123"})
    res = client.post("/api/auth/login", json={"username": username, "password": "secret123"})
    return {"Authorization": f"Bearer {res.json()['token']}"}


@pytest.mark.parametrize("path, expected", [
    ("/", "get_move"),
    ("/games", "RPS Chess 9×9"),
    ("/games/connect4", "connect4_template.py"),
    ("/games/caro", "caro_template.py"),
    ("/games/rps9x9", "bot_template.py"),
    ("/play/connect4", "games.js"),
    ("/play/caro", "board_view.js"),
    ("/play/rps9x9", "GameKit"),
    ("/guide", "bot đầu tiên"),
    ("/guide/organizer", "--tunnel"),
    ("/grade", "Tự chấm"),
    ("/leaderboard", "Bảng xếp hạng"),
])
def test_public_pages_render(client, path, expected):
    res = client.get(path)
    assert res.status_code == 200
    assert expected in res.text


def test_unknown_game_pages_return_404(client):
    assert client.get("/games/chess").status_code == 404
    assert client.get("/play/chess").status_code == 404


def test_navbar_links_to_new_sections(client):
    text = client.get("/").text
    for href in ('href="/games"', 'href="/guide"', 'href="/leaderboard"', 'href="/grade"'):
        assert href in text


def test_home_shows_lan_address_instead_of_localhost(client, monkeypatch):
    monkeypatch.delenv("PUBLIC_URL", raising=False)
    monkeypatch.setattr("server.network.get_lan_ip", lambda: "10.1.2.3")
    res = TestClient(app, base_url="http://localhost:8000").get("/")
    assert "http://10.1.2.3:8000" in res.text

    monkeypatch.setenv("PUBLIC_URL", "https://demo.trycloudflare.com/")
    assert "https://demo.trycloudflare.com" in client.get("/").text


def test_starter_kit_zip_contains_offline_tools(client):
    res = client.get("/download/starter-kit.zip")
    assert res.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(res.content)).namelist()
    for required in (
        "codeduel-kit/README.txt",
        "codeduel-kit/starter_kit/grade.py",
        "codeduel-kit/starter_kit/local_arena.py",
        "codeduel-kit/starter_kit/connect4_template.py",
        "codeduel-kit/engine/games/grid.py",
        "codeduel-kit/engine/grader.py",
        "codeduel-kit/server/bosses/novice_bot.py",
    ):
        assert required in names
    assert not any("__pycache__" in name for name in names)


def test_leaderboard_csv_excludes_admin(client):
    db = SessionLocal()
    try:
        admin = User(username="boss_admin", is_admin=True)
        admin.set_password("adminpass1")
        db.add_all([admin, User(username="student_a", elo=1300, wins=2, password_hash="x")])
        db.commit()
    finally:
        db.close()
    res = client.get("/api/leaderboard/export.csv")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    body = res.content.decode("utf-8-sig")
    assert body.splitlines()[0].startswith("rank,username,elo")
    assert "student_a,1300" in body
    assert "boss_admin" not in body


def test_grade_api_runs_uploaded_file(client):
    anonymous = TestClient(app)
    assert anonymous.post("/api/grade", data={"game_type": "connect4"}).status_code == 401
    headers = _login(client, "grader_kid")

    # No active Connect Four bot yet and no file: refused.
    res = client.post("/api/grade", headers=headers, data={"game_type": "connect4"})
    assert res.status_code == 400

    bad = client.post("/api/grade", headers=headers, data={"game_type": "connect4"},
                      files={"file": ("evil.py", b"import os\n", "text/x-python")})
    assert bad.status_code == 400

    source = (STARTER / "connect4_bot.py").read_bytes()
    res = client.post("/api/grade", headers=headers, data={"game_type": "connect4"},
                      files={"file": ("c4.py", source, "text/x-python")})
    assert res.status_code == 202
    job_id = res.json()["job_id"]

    deadline = time.time() + 60
    job = {}
    while time.time() < deadline:
        job = client.get(f"/api/grade/{job_id}", headers=headers).json()
        if job["status"] in ("done", "error"):
            break
        time.sleep(0.3)
    assert job["status"] == "done"
    assert job["report"]["valid"] is True
    assert 0 <= job["report"]["score"] <= 10
    assert len(job["progress"]) == 8

    other = _login(client, "nosy_kid")
    assert client.get(f"/api/grade/{job_id}", headers=other).status_code == 404


def test_session_cookie_secure_follows_https(monkeypatch):
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    for base, secure in (("http://testserver", False), ("https://testserver", True)):
        c = TestClient(app, base_url=base)
        c.post("/api/auth/register", json={"username": "cookie_kid", "password": "secret123"})
        res = c.post("/api/auth/login", json={"username": "cookie_kid", "password": "secret123"})
        assert ("secure" in res.headers["set-cookie"].lower()) is secure


def test_parse_tunnel_url():
    line = "2026-10-17T10:00:00Z INF |  https://quick-brown-fox.trycloudflare.com  |"
    assert parse_tunnel_url(line) == "https://quick-brown-fox.trycloudflare.com"
    assert parse_tunnel_url("INF Starting tunnel") is None


def test_responses_are_gzip_compressed(client):
    res = client.get("/guide", headers={"Accept-Encoding": "gzip"})
    assert res.headers.get("content-encoding") == "gzip"


def test_organizer_has_peer_review_rubric(client):
    page = client.get("/guide/organizer").text
    assert 'aria-label="Tiêu chí đánh giá chéo"' in page
    assert "phân bố chuẩn" in page


def test_default_catalog_and_admin_publication(client):
    page = client.get("/games").text
    assert 'href="/games/rps9x9"' in page
    assert 'href="/games/connect4"' not in page
    assert 'href="/games/caro"' not in page
    headers = _login(client, "catalog_student")
    assert client.post("/api/admin/settings", headers=headers,
                       json={"catalog_games": ["rps9x9", "caro"]}).status_code == 403
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "catalog_student").first()
        user.is_admin = True
        db.commit()
    finally:
        db.close()
    response = client.post("/api/admin/settings", headers=headers,
                           json={"catalog_games": ["rps9x9", "caro"]})
    assert response.status_code == 200
    page = client.get("/games").text
    assert 'href="/games/caro"' in page
    assert 'href="/games/connect4"' not in page
    assert client.post("/api/admin/settings", headers=headers,
                       json={"catalog_games": ["unknown"]}).status_code == 400
    assert client.post("/api/admin/settings", headers=headers,
                       json={"catalog_games": ["rps9x9"]}).status_code == 200
    assert 'href="/games/caro"' not in client.get("/games").text
