"""Self-grading API: run a bot against the reference ladder and report a score.

Grading plays a dozen short games in subprocesses, so it runs in a background
thread and the browser polls for progress. A small semaphore caps how many
gradings run at once so a whole class pressing the button together cannot
starve ranked matches of CPU.
"""

from __future__ import annotations

import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from engine.games import GAMES
from engine.grader import grade_bot
from engine.sandbox import validate_bot_source
from server.database import get_db
from server.games import get_active_bot, get_active_game
from server.models import User
from server.routes.auth import get_current_user

router = APIRouter(prefix="/grade", tags=["grade"])

MAX_CONCURRENT_GRADINGS = 2
MAX_JOBS_KEPT = 200
_grading_slots = threading.BoundedSemaphore(MAX_CONCURRENT_GRADINGS)
_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _run_job(job_id: str, bot_path: Path, game_type: str, cleanup: Optional[Path]) -> None:
    """Background worker: wait for a free slot, grade, store the report."""
    job = _jobs[job_id]
    try:
        with _grading_slots:
            job["status"] = "running"
            job["report"] = grade_bot(
                bot_path, game_type, progress=lambda line: job["progress"].append(line)
            )
            job["status"] = "done"
    except Exception as exc:  # pragma: no cover - defensive, reported to the UI
        job["status"] = "error"
        job["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if cleanup is not None:
            cleanup.unlink(missing_ok=True)


def _remember(job: Dict[str, Any]) -> None:
    """Store a job, discarding the oldest ones beyond MAX_JOBS_KEPT."""
    with _jobs_lock:
        _jobs[job["id"]] = job
        while len(_jobs) > MAX_JOBS_KEPT:
            _jobs.pop(next(iter(_jobs)))


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_grading(
    game_type: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Start grading an uploaded file, or the user's active bot for the game.

    Uploaded files are only used for this grading run; they are not saved as
    the user's bot, so students can experiment freely.
    """
    game_type = (game_type or get_active_game(db)).strip()
    if game_type not in GAMES:
        raise HTTPException(status_code=400, detail="Unknown game type.")

    cleanup: Optional[Path] = None
    if file is not None and file.filename:
        if not file.filename.endswith(".py"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a Python (.py) file")
        try:
            source = (await file.read()).decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File content must be valid UTF-8 text")
        is_valid, error = validate_bot_source(source)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Bot validation failed: {error}")
        handle = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
        with handle:
            handle.write(source)
        bot_path = cleanup = Path(handle.name)
        bot_label = file.filename
    else:
        bot = get_active_bot(db, current_user.id, game_type)
        if bot is None:
            raise HTTPException(
                status_code=400,
                detail=f"No active bot for {GAMES[game_type]['name']}. Upload a file to grade.",
            )
        bot_path = Path(bot.filepath)
        bot_label = bot.filename

    job = {
        "id": uuid.uuid4().hex,
        "user_id": current_user.id,
        "game_type": game_type,
        "bot": bot_label,
        "status": "queued",
        "progress": [],
        "report": None,
        "error": None,
    }
    _remember(job)
    threading.Thread(
        target=_run_job, args=(job["id"], bot_path, game_type, cleanup), daemon=True
    ).start()
    return {"job_id": job["id"], "status": job["status"]}


@router.get("/{job_id}")
def grading_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return progress lines and, once finished, the grading report."""
    job = _jobs.get(job_id)
    if job is None or job["user_id"] != current_user.id:
        raise HTTPException(status_code=404, detail="Grading job not found.")
    return {key: value for key, value in job.items() if key != "user_id"}
