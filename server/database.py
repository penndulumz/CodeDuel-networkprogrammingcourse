"""Database connection, SQLite engine configuration, and session management."""

import os
from typing import Generator
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Database URL defaulting to SQLite app.db, configurable via DATABASE_URL environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configure SQLite connections with WAL mode and foreign key support.

    Executes PRAGMA journal_mode=WAL and PRAGMA synchronous=NORMAL for concurrent
    performance and reliability, and enables foreign keys for relational integrity.
    """
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        # Silently pass if connected to non-SQLite database
        pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency generator that yields a database session and ensures clean closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Create registered tables and add live tournament columns to older SQLite files."""
    from server import models  # noqa: F401
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    # SQLite create_all does not add newly declared columns to an existing database.
    if eng.dialect.name == "sqlite":
        with eng.begin() as connection:
            tables = inspect(connection).get_table_names()
            if "matches" in tables:
                match_columns = {
                    column["name"] for column in inspect(connection).get_columns("matches")
                }
                if "bracket_match_id" not in match_columns:
                    connection.execute(
                        text("ALTER TABLE matches ADD COLUMN bracket_match_id INTEGER")
                    )
                if "live_moves" not in match_columns:
                    connection.execute(
                        text("ALTER TABLE matches ADD COLUMN live_moves TEXT NOT NULL DEFAULT '[]'")
                    )
                connection.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_matches_bracket_match_id "
                        "ON matches (bracket_match_id)"
                    )
                )
            if "bracket_matches" in tables:
                bracket_columns = {
                    column["name"]
                    for column in inspect(connection).get_columns("bracket_matches")
                }
                if "game_results" not in bracket_columns:
                    connection.execute(
                        text(
                            "ALTER TABLE bracket_matches ADD COLUMN "
                            "game_results TEXT NOT NULL DEFAULT '[]'"
                        )
                    )
