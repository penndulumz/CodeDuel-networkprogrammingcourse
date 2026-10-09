"""Tests for single administrator security enforcement and credential synchronization."""

import os
from fastapi.testclient import TestClient
from server.main import app
from server.database import SessionLocal, init_db
from server.models import User
from main import seed_admin_and_starter_bots


def test_register_admin_username_rejected():
    """Verify that registering with reserved 'admin' username is strictly rejected."""
    init_db()
    client = TestClient(app)
    # Rejects exact or case-insensitive match with admin username
    res = client.post(
        "/api/auth/register",
        json={"username": "Admin", "password": "password123"},
    )
    assert res.status_code == 400
    detail = res.json()["detail"].lower()
    assert "reserved" in detail or "already taken" in detail or "admin" in detail


def test_single_admin_demotion_invariant():
    """Verify that only ONE administrator account can exist; any rogue admin is demoted."""
    init_db()
    db = SessionLocal()
    try:
        # Create a rogue admin
        rogue = db.query(User).filter(User.username == "rogue_user").first()
        if not rogue:
            rogue = User(username="rogue_user", is_admin=True, elo=1200)
            rogue.set_password("secret123")
            db.add(rogue)
        else:
            rogue.is_admin = True
        db.commit()

        # Run seeder
        seed_admin_and_starter_bots(db)

        # Verify rogue was demoted and only official admin remains
        db.refresh(rogue)
        assert rogue.is_admin is False

        target_admin_user = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
        admins = db.query(User).filter(User.is_admin == True).all()
        assert len(admins) == 1
        assert admins[0].username.lower() == target_admin_user
    finally:
        db.close()
