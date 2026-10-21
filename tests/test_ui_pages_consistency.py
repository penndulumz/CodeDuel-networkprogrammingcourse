"""Integration tests for Unified Clubhouse 2.0 UI consistency and responsiveness."""

from fastapi.testclient import TestClient
from server.database import init_db
from server.main import app


def test_core_pages_render_with_clubhouse_theme():
    init_db()
    client = TestClient(app)

    routes = ["/", "/bracket", "/games", "/guide", "/grade", "/leaderboard"]
    for route in routes:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} failed with status {resp.status_code}"
        assert "clubhouse.css" in resp.text
        assert "Be+Vietnam+Pro" in resp.text


def test_clubhouse_css_contains_bracket_and_accessibility_tokens():
    with open("web/static/css/clubhouse.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Touch accessibility and button sizes
    assert "min-height:" in css or "min-height" in css
    # Bracket and champion card rules in clubhouse theme
    assert ".champion-card" in css
    assert ".bracket-match" in css
    assert ".live-projections" in css
    # Mobile sticker transform prevention to avoid horizontal overflow
    assert "transform:none" in css or "transform: none" in css
