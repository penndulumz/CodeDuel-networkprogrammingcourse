"""Session-wide safety net for local development data.

Several test modules reset state by deleting app.db, bots/ and replays/ in the
working directory. Those are the same paths the dev server uses, so running
pytest used to wipe a developer's local database, uploaded bots and replays.

This fixture moves those artefacts aside before the session and puts them back
afterwards, so `pytest` can be run at any time without losing local data.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_ARTIFACTS = ["app.db", "app.db-shm", "app.db-wal", "bots", "replays"]


def _remove(path: Path) -> None:
    """Delete a file or directory if it exists."""
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


@pytest.fixture(scope="session", autouse=True)
def preserve_dev_data():
    """Back up dev artefacts before the test session and restore them after."""
    backup_dir = Path(tempfile.mkdtemp(prefix="codeduel-devdata-"))
    saved = []
    for name in DEV_ARTIFACTS:
        source = REPO_ROOT / name
        if source.exists():
            shutil.move(str(source), str(backup_dir / name))
            saved.append(name)
    try:
        yield
    finally:
        # Close pooled SQLite handles so Windows allows the files to be replaced.
        try:
            from server.database import engine

            engine.dispose()
        except Exception:
            pass
        for name in DEV_ARTIFACTS:
            _remove(REPO_ROOT / name)
        for name in saved:
            shutil.move(str(backup_dir / name), str(REPO_ROOT / name))
        shutil.rmtree(backup_dir, ignore_errors=True)
