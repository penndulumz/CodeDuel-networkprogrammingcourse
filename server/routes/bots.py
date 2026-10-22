"""Bot upload and management API routes."""

from __future__ import annotations

import hashlib
import json
import uuid
import zipfile
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from engine.games import GAMES
from engine.sandbox import validate_bot_source
from server.database import DATA_DIR, get_db
from server.games import get_active_bot, get_active_game
from server.models import Bot, User
from server.routes.auth import get_current_user

router = APIRouter(prefix="/bots", tags=["bots"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_bot(
    file: UploadFile = File(...),
    game_type: Optional[str] = Form(None),
    client_submission_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Upload a Python bot or offline package, then save and activate it.

    The bot is registered for `game_type` (defaults to the event's active game)
    and replaces only the user's previous active bot for that same game.
    """
    if game_type is None or not game_type.strip():
        game_type = get_active_game(db)
    game_type = game_type.strip()
    if game_type not in GAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown game '{game_type}'. Supported: {', '.join(GAMES)}",
        )
    raw_filename = Path(file.filename or "bot.py").name
    if Path(raw_filename).suffix.lower() not in {".py", ".zip"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a Python bot (.py) or an offline submission package (.zip)",
        )

    try:
        content_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        )
    if len(content_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Upload package exceeds 2 MB")

    requested_submission_id = client_submission_id
    client_submission_id = None
    bot_filename = raw_filename
    if Path(raw_filename).suffix.lower() == ".zip":
        try:
            source_code, bot_filename, package_game, package_submission_id = _read_offline_package(content_bytes)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if requested_submission_id and requested_submission_id != package_submission_id:
            raise HTTPException(status_code=400, detail="Submission ID does not match the package")
        client_submission_id = package_submission_id
        if package_game != game_type:
            raise HTTPException(
                status_code=400,
                detail=f"Package is for '{package_game}', but the selected game is '{game_type}'",
            )
    else:
        try:
            source_code = content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bot content must be valid UTF-8 text",
            ) from exc
        if requested_submission_id:
            try:
                client_submission_id = str(uuid.UUID(requested_submission_id))
            except (ValueError, TypeError, AttributeError) as exc:
                raise HTTPException(status_code=400, detail="Invalid submission ID") from exc

    if client_submission_id:
        existing = (
            db.query(Bot)
            .filter(
                Bot.user_id == current_user.id,
                Bot.client_submission_id == client_submission_id,
            )
            .first()
        )
        if existing:
            if existing.is_deleted:
                raise HTTPException(
                    status_code=409,
                    detail="This submission was deleted. Upload it again as a new submission.",
                )
            try:
                existing_hash = hashlib.sha256(Path(existing.filepath).read_bytes()).hexdigest()
            except OSError:
                existing_hash = None
            if existing_hash != hashlib.sha256(source_code.encode("utf-8")).hexdigest():
                raise HTTPException(
                    status_code=409,
                    detail="This submission ID was already used for different bot contents. Create a new submission.",
                )
            return _upload_receipt(existing, client_submission_id)

    # Validate syntax and security rules via AST sandbox
    is_valid, error_msg = validate_bot_source(source_code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bot validation failed: {error_msg}",
        )

    # Save bot script to disk in bots/ directory
    bots_dir = (DATA_DIR / "bots").resolve()
    bots_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(datetime.now(timezone.utc).timestamp())
    safe_stem = Path(bot_filename).stem.replace(" ", "_")
    unique_suffix = (client_submission_id or uuid.uuid4().hex)[:8]
    target_filename = f"user_{current_user.id}_{timestamp}_{unique_suffix}_{safe_stem}.py"
    target_path = bots_dir / target_filename
    target_path.write_text(source_code, encoding="utf-8")

    # Deactivate the user's existing active bot for this game only
    db.query(Bot).filter(
        Bot.user_id == current_user.id,
        Bot.is_active == True,  # noqa: E712
        Bot.game_type == game_type,
    ).update({"is_active": False})

    # Create new active Bot record
    new_bot = Bot(
        user_id=current_user.id,
        filename=bot_filename,
        filepath=str(target_path),
        game_type=game_type,
        client_submission_id=client_submission_id,
        is_active=True,
    )
    db.add(new_bot)
    db.commit()
    db.refresh(new_bot)

    return _upload_receipt(new_bot, client_submission_id)


def _upload_receipt(bot: Bot, submission_id: str | None) -> Dict[str, Any]:
    """Return the server-confirmed receipt for an accepted submission."""
    received_at = bot.uploaded_at.isoformat() if bot.uploaded_at else datetime.now(timezone.utc).isoformat()
    return {
        "id": bot.id,
        "filename": bot.filename,
        "is_active": bot.is_active,
        "game_type": bot.game_type,
        "uploaded_at": received_at,
        "submission_id": submission_id,
        "receipt": f"CD-{bot.id}-{(submission_id or 'ONLINE')[:8]}",
        "received_at": received_at,
        "message": "Server received this submission.",
    }


def _read_offline_package(content: bytes) -> tuple[str, str, str, str]:
    """Read and verify a starter-kit submission ZIP without extracting paths."""
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) != 2 or set(names) != {"manifest.json", "bot.py"}:
                raise ValueError("Package must contain only manifest.json and bot.py")
            if any(info.file_size > 1024 * 1024 for info in archive.infolist()):
                raise ValueError("Bot package contents exceed 1 MB")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            source_bytes = archive.read("bot.py")
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError, OSError, RuntimeError) as exc:
        raise ValueError("Invalid offline submission ZIP") from exc

    if not isinstance(manifest, dict) or manifest.get("format") != "codeduel-offline-submission":
        raise ValueError("Unsupported offline submission package")
    if manifest.get("version") != 1:
        raise ValueError("Unsupported offline package version")
    submission_id = manifest.get("submission_id")
    try:
        submission_id = str(uuid.UUID(str(submission_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Offline package has an invalid submission ID") from exc

    filename = manifest.get("bot_filename")
    game_type = manifest.get("game_type")
    if (
        not isinstance(filename, str)
        or len(filename) > 255
        or Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
        or not filename.lower().endswith(".py")
    ):
        raise ValueError("Offline package has an invalid bot filename")
    if not isinstance(game_type, str) or game_type not in GAMES:
        raise ValueError("Offline package has an unknown game")
    if hashlib.sha256(source_bytes).hexdigest() != manifest.get("sha256"):
        raise ValueError("Bot checksum does not match the offline package manifest")
    try:
        source_code = source_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Bot content must be valid UTF-8 text") from exc
    return source_code, filename, game_type, submission_id


@router.get("", response_model=List[Dict[str, Any]])
def list_my_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all bot submissions uploaded by the authenticated user."""
    bots = (
        db.query(Bot)
        .filter(Bot.user_id == current_user.id, Bot.is_deleted == False)  # noqa: E712
        .order_by(Bot.uploaded_at.desc())
        .all()
    )
    return [
        {
            "id": b.id,
            "filename": b.filename,
            "is_active": b.is_active,
            "game_type": b.game_type,
            "uploaded_at": b.uploaded_at.isoformat(),
            "receipt": f"CD-{b.id}-{(b.client_submission_id or 'ONLINE')[:8]}",
        }
        for b in bots
    ]


@router.get("/active")
def get_my_active_bot(
    game_type: Optional[str] = Query(None, description="Game slug; defaults to the active game"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve the authenticated user's active bot for a game (default: active game)."""
    bot = get_active_bot(db, current_user.id, game_type or get_active_game(db))
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bot found",
        )

    return {
        "id": bot.id,
        "filename": bot.filename,
        "is_active": bot.is_active,
        "game_type": bot.game_type,
        "uploaded_at": bot.uploaded_at.isoformat(),
    }


@router.post("/{bot_id}/activate")
def activate_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Mark a specific previously uploaded bot as the active bot."""
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.user_id == current_user.id, Bot.is_deleted == False)  # noqa: E712
        .first()
    )
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found",
        )

    # Only one active bot per game: deactivate siblings for the same game
    db.query(Bot).filter(
        Bot.user_id == current_user.id,
        Bot.game_type == bot.game_type,
    ).update({"is_active": False})

    bot.is_active = True
    db.commit()
    db.refresh(bot)

    return {
        "id": bot.id,
        "filename": bot.filename,
        "is_active": bot.is_active,
        "game_type": bot.game_type,
        "uploaded_at": bot.uploaded_at.isoformat(),
    }


@router.post("/deactivate")
def deactivate_all_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Leave the user without an active bot for any game."""
    changed = (
        db.query(Bot)
        .filter(Bot.user_id == current_user.id, Bot.is_active == True, Bot.is_deleted == False)  # noqa: E712
        .update({"is_active": False}, synchronize_session=False)
    )
    db.commit()
    return {"deactivated": changed}


@router.delete("/{bot_id}")
def delete_bot(
    bot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Delete one of the authenticated user's saved bots and its source file."""
    bot = (
        db.query(Bot)
        .filter(Bot.id == bot_id, Bot.user_id == current_user.id, Bot.is_deleted == False)  # noqa: E712
        .first()
    )
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found")

    filepath = Path(bot.filepath)
    bots_dir = (DATA_DIR / "bots").resolve()
    bot.is_active = False
    bot.is_deleted = True
    db.commit()

    # Only remove files inside this application's bot storage directory.
    try:
        resolved_filepath = filepath.resolve()
        resolved_filepath.relative_to(bots_dir)
    except (OSError, ValueError):
        resolved_filepath = None
    if resolved_filepath and resolved_filepath.is_file():
        try:
            resolved_filepath.unlink()
        except OSError:
            # The database record is already removed; an orphaned source file
            # is harmless and must not turn a successful delete into an error.
            pass

    return {"id": bot_id, "deleted": True, "is_active": False}
