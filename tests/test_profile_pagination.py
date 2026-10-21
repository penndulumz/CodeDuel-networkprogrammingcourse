"""Verify history pagination against an isolated database without touching app.db."""

from datetime import datetime
from importlib import import_module

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from server.database import Base
from server.models import Match, User


def test_history_pages_are_stable_and_scoped_to_user(monkeypatch):
    main = import_module("server.main")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            users = [User(username=name, password_hash="test") for name in ("one", "two", "three")]
            db.add_all(users)
            db.flush()
            for _ in range(23):
                db.add(Match(player1_id=users[0].id, player2_id=users[1].id,
                             created_at=datetime(2026, 1, 1)))
            db.add(Match(player1_id=users[1].id, player2_id=users[2].id))
            db.commit()
            monkeypatch.setattr(main, "_get_optional_user", lambda request, session: users[0])
            request = Request({"type": "http", "method": "GET", "path": "/profile",
                               "headers": [], "query_string": b"", "scheme": "http",
                               "server": ("test", 80)})
            contexts = [main.profile_page(request, db=db, page=p).context for p in (1, 2, 999)]
            assert [len(c["user_matches"]) for c in contexts] == [10, 10, 3]
            assert contexts[-1]["history_page"] == 3
            assert contexts[-1]["history_total"] == 23
            assert contexts[-1]["history_start"] == 21
            assert contexts[-1]["history_end"] == 23
            ids = [m.id for c in contexts for m in c["user_matches"]]
            assert ids == list(range(23, 0, -1))
            db.query(Match).delete()
            db.commit()
            empty = main.profile_page(request, db=db, page=99).context
            assert empty["history_page"] == 1
            assert empty["history_start"] == 0
            assert empty["user_matches"] == []
    finally:
        engine.dispose()
