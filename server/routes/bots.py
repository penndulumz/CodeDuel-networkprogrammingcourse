"""Bot upload and management API routes."""

from __future__ import annotations

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Upload a Python bot file, validate with AST sandbox, save to disk, and mark active.

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
    raw_filename = file.filename or "bot.py"
    if not raw_filename.endswith(".py"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a Python (.py) file",
        )

    try:
        content_bytes = await file.read()
        source_code = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content must be valid UTF-8 text",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        )

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
    safe_stem = Path(raw_filename).stem.replace(" ", "_")
    target_filename = f"user_{current_user.id}_{timestamp}_{safe_stem}.py"
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
        filename=raw_filename,
        filepath=str(target_path),
        game_type=game_type,
        is_active=True,
    )
    db.add(new_bot)
    db.commit()
    db.refresh(new_bot)

    return {
        "id": new_bot.id,
        "filename": new_bot.filename,
        "filepath": new_bot.filepath,
        "is_active": new_bot.is_active,
        "game_type": new_bot.game_type,
        "uploaded_at": new_bot.uploaded_at.isoformat(),
    }


@router.get("", response_model=List[Dict[str, Any]])
def list_my_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List all bot submissions uploaded by the authenticated user."""
    bots = (
        db.query(Bot)
        .filter(Bot.user_id == current_user.id)
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
        .filter(Bot.id == bot_id, Bot.user_id == current_user.id)
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
