"""Tests for WAN deployment environment configuration."""

from server.main import get_allowed_origins


def test_allowed_origins_defaults_to_local_development(monkeypatch):
    """CORS origins should default to local development URLs."""
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert get_allowed_origins() == [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


def test_allowed_origins_reads_comma_separated_wan_urls(monkeypatch):
    """CORS origins should be configurable for WAN HTTPS tunnel URLs."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://demo.trycloudflare.com, https://codeduel.example.com",
    )

    assert get_allowed_origins() == [
        "https://demo.trycloudflare.com",
        "https://codeduel.example.com",
    ]


def test_allowed_origins_ignores_empty_entries(monkeypatch):
    """CORS origin parsing should ignore empty comma-separated entries."""
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://demo.trycloudflare.com, , http://localhost:8000,",
    )

    assert get_allowed_origins() == [
        "https://demo.trycloudflare.com",
        "http://localhost:8000",
    ]