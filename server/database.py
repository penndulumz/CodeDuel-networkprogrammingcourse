"""Database connection, SQLite engine configuration, and session management."""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Writable directory for the SQLite database, uploaded bots and replays. Point
# DATA_DIR at a persistent volume (e.g. /data on Render/Railway) in production.
DATA_DIR = Path(os.getenv("DATA_DIR", "."))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database URL defaulting to SQLite app.db inside DATA_DIR, configurable via DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}")

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


# Columns added after the first release. create_all() never alters existing
# tables, so older app.db files get these columns added in place on startup.
# Format: (table, column, SQL type and default).
ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("bots", "game_type", "VARCHAR(32) NOT NULL DEFAULT 'rps9x9'"),
    ("matches", "game_type", "VARCHAR(32) NOT NULL DEFAULT 'rps9x9'"),
]


def _add_missing_columns(eng) -> None:
    """Add columns from ADDED_COLUMNS that an existing database is missing."""
    inspector = inspect(eng)
    existing_tables = set(inspector.get_table_names())
    with eng.begin() as conn:
        for table, column, ddl in ADDED_COLUMNS:
            if table not in existing_tables:
                continue
            columns = {col["name"] for col in inspector.get_columns(table)}
            if column not in columns:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db(target_engine=None) -> None:
    """Create all database tables and upgrade older schemas in place."""
    from server import models  # noqa: F401
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    _add_missing_columns(eng)
