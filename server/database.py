"""Database connection, SQLite engine configuration, and session management."""

import os
import logging
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
logger = logging.getLogger(__name__)


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
    ("bots", "client_submission_id", "VARCHAR(64)"),
    ("bots", "is_deleted", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("matches", "game_type", "VARCHAR(32) NOT NULL DEFAULT 'rps9x9'"),
    ("matches", "bracket_match_id", "INTEGER"),
    ("matches", "live_moves", "TEXT NOT NULL DEFAULT '[]'"),
    ("bracket_matches", "game_results", "TEXT NOT NULL DEFAULT '[]'"),
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
        if "matches" in existing_tables:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_matches_bracket_match_id "
                    "ON matches (bracket_match_id)"
                )
            )
        if "bots" in existing_tables:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_bots_user_client_submission "
                    "ON bots (user_id, client_submission_id) "
                    "WHERE client_submission_id IS NOT NULL"
                )
            )


def _archive_incompatible_tables(eng) -> None:
    """Preserve malformed legacy tables so create_all can build the current schema.

    ``create_all`` intentionally leaves existing tables untouched. If an older
    release created a partial table with a current table's name, ORM queries
    fail with missing-column errors. Renaming retains its rows for recovery.
    """
    inspector = inspect(eng)
    existing_tables = set(inspector.get_table_names())
    expected_tables = Base.metadata.tables
    incompatible = {}
    for table_name in ("qualifier_tournaments", "qualifier_matches"):
        if table_name not in existing_tables or table_name not in expected_tables:
            continue
        actual = {column["name"] for column in inspector.get_columns(table_name)}
        missing = set(expected_tables[table_name].columns.keys()) - actual
        if missing:
            incompatible[table_name] = missing
    if not incompatible:
        return

    # These two tables reference each other. Archive the pair together so a
    # surviving child table cannot retain a foreign key to an archived parent.
    with eng.begin() as conn:
        for table_name in ("qualifier_tournaments", "qualifier_matches"):
            if table_name not in existing_tables or table_name not in expected_tables:
                continue
            suffix = 1
            archive_name = f"{table_name}_legacy"
            while archive_name in existing_tables:
                suffix += 1
                archive_name = f"{table_name}_legacy_{suffix}"
            conn.execute(text(f'ALTER TABLE "{table_name}" RENAME TO "{archive_name}"'))
            existing_tables.add(archive_name)
            existing_tables.remove(table_name)
            logger.warning(
                "Archived incompatible database table %s as %s; missing columns: %s",
                table_name,
                archive_name,
                ", ".join(sorted(incompatible.get(table_name, set()))),
            )


def init_db(target_engine=None) -> None:
    """Create current tables and upgrade or preserve incompatible old schemas."""
    from server import models  # noqa: F401
    eng = target_engine or engine
    _archive_incompatible_tables(eng)
    Base.metadata.create_all(bind=eng)
    _add_missing_columns(eng)
