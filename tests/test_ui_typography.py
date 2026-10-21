"""Tests for Unified Clubhouse 2.0 web fonts and typography configuration."""

from fastapi.testclient import TestClient
from server.database import init_db
from server.main import app


def test_base_template_loads_be_vietnam_pro_and_jetbrains_mono():
    init_db()
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # Google Fonts preconnect and links
    assert "https://fonts.googleapis.com" in html
    assert "Be+Vietnam+Pro" in html
    assert "JetBrains+Mono" in html


def test_clubhouse_css_typography_tokens():
    with open("web/static/css/clubhouse.css", "r", encoding="utf-8") as f:
        content = f.read()

    assert "--font-sans" in content
    assert "Be Vietnam Pro" in content
    # Trebuchet MS should not be the primary font
    assert '--font-sans:"Trebuchet MS"' not in content
    assert '--font-display:"Trebuchet MS"' not in content


def test_style_css_typography_tokens():
    with open("web/static/css/style.css", "r", encoding="utf-8") as f:
        content = f.read()

    assert "--font-sans" in content
    assert "Be Vietnam Pro" in content
    assert "JetBrains Mono" in content
    # Bahnschrift should not be the primary display font
    assert '--font-display: "Bahnschrift"' not in content
