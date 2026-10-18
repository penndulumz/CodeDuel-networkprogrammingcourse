"""FastAPI application entrypoint for Battlecode 9x9 RPS Platform.

Configures CORS, database initialization lifecycle, mounts all REST API routes
for authentication, bot management, match challenges, leaderboard rankings, and
tournament administration, and serves static files and Jinja2 web UI templates.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from server.database import get_db, init_db
from server.bracket import ROUND_ORDER, get_final_results, is_bracket_finished
from server.models import Bot, BracketMatch, Match, User
from server.routes import admin, auth, bots, leaderboard, matches
from server.routes.admin import _get_all_settings_dict
from server.routes.auth import ACTIVE_SESSIONS, get_token_from_request
from server.routes.matches import _is_portal_open_now
from engine.game import create_initial_board


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "web" / "static"
TEMPLATES_DIR = BASE_DIR / "web" / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing startup and shutdown routines."""
    init_db()
    yield


app = FastAPI(
    title="Battlecode 9x9 RPS Platform API",
    description="REST API for the 9x9 Rock-Paper-Scissors Chess tournament platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for local web client and remote tunnel access
def get_allowed_origins() -> List[str]:
    """Return the configured CORS allowed origins for local or WAN deployment."""
    allowed_origins_env = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    )

    return [
        origin.strip()
        for origin in allowed_origins_env.split(",")
        if origin.strip()
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for web UI
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates configuration
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount all feature routes under /api
app.include_router(auth.router, prefix="/api")
app.include_router(bots.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/api/users/{user_id}/rating-history", tags=["users"])
def get_user_rating_history_alias(
    user_id: int,
    limit: int = Query(50, ge=5, le=100),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve chronological Elo trajectory for a specific user ID."""
    return leaderboard.get_single_user_rating_history(user_id=user_id, limit=limit, db=db)



def _get_optional_user(request: Request, db: Session) -> User | None:
    """Retrieve authenticated User from session cookie/header without raising HTTP 401."""
    token = get_token_from_request(request)
    if token and token in ACTIVE_SESSIONS:
        user_id = ACTIVE_SESSIONS[token]
        return db.query(User).filter(User.id == user_id).first()
    return None


# ================== WEB UI HTML ROUTES ==================


@app.get("/", response_class=HTMLResponse, tags=["web"])
def home_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the homepage leaderboard and FFA challenge portal."""
    current_user = _get_optional_user(request, db)
    users = (
        db.query(User)
        .order_by(User.elo.desc(), User.wins.desc(), User.id.asc())
        .all()
    )

    ranking_list: List[Dict[str, Any]] = []
    for rank_idx, u in enumerate(users, start=1):
        has_active = any(b.is_active for b in u.bots)
        ranking_list.append({
            "rank": rank_idx,
            "id": u.id,
            "username": u.username,
            "elo": u.elo,
            "wins": u.wins,
            "losses": u.losses,
            "draws": u.draws,
            "has_active_bot": has_active,
        })

    settings = _get_all_settings_dict(db)
    is_portal_open = _is_portal_open_now(db)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "leaderboard": ranking_list,
            "is_portal_open": is_portal_open,
            "daily_multiplier_x": settings.get("daily_multiplier_x", 1.5),
            "current_user": current_user,
        },
    )


@app.get("/login", response_class=HTMLResponse, tags=["web"])
def login_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the user login page."""
    current_user = _get_optional_user(request, db)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"current_user": current_user},
    )


@app.get("/register", response_class=HTMLResponse, tags=["web"])
def register_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the user registration page."""
    current_user = _get_optional_user(request, db)
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"current_user": current_user},
    )


@app.get("/profile", response_class=HTMLResponse, tags=["web"])
def profile_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the user profile, bot upload drop zone, and match history page."""
    current_user = _get_optional_user(request, db)
    user_bots: List[Bot] = []
    user_matches: List[Match] = []

    if current_user:
        user_bots = (
            db.query(Bot)
            .filter(Bot.user_id == current_user.id)
            .order_by(Bot.uploaded_at.desc())
            .all()
        )
        user_matches = (
            db.query(Match)
            .filter(or_(Match.player1_id == current_user.id, Match.player2_id == current_user.id))
            .order_by(Match.created_at.desc())
            .limit(20)
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "current_user": current_user,
            "user_bots": user_bots,
            "user_matches": user_matches,
        },
    )


@app.get("/replay/{match_id}", response_class=HTMLResponse, tags=["web"])
def replay_page(
    match_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the interactive 9x9 visual replay arena."""
    current_user = _get_optional_user(request, db)
    match = db.query(Match).filter(Match.id == match_id).first()
    return templates.TemplateResponse(
        request=request,
        name="replay.html",
        context={
            "match_id": match_id,
            "match": match,
            "current_user": current_user,
        },
    )



@app.get("/admin", response_class=HTMLResponse, tags=["web"])
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Render tournament configuration management and bracket generator page."""
    current_user = _get_optional_user(request, db)
    if current_user is None:
        return RedirectResponse(
            url="/login?next=/admin",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )

    settings = _get_all_settings_dict(db)
    bracket_matches = (
        db.query(BracketMatch)
        .order_by(BracketMatch.id.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "settings": settings,
            "bracket_matches": bracket_matches,
            "current_user": current_user,
        },
    )


@app.get("/bracket", response_class=HTMLResponse, tags=["web"])
def bracket_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the tournament bracket elimination tree and match pairings."""
    current_user = _get_optional_user(request, db)
    bracket_matches = (
        db.query(BracketMatch)
        .order_by(BracketMatch.id.asc())
        .all()
    )

    present_rounds = {bm.round_name for bm in bracket_matches}
    bracket_rounds = [name for name in ROUND_ORDER if name in present_rounds]
    final_results = (
        get_final_results(db) if is_bracket_finished(bracket_matches) else []
    )

    return templates.TemplateResponse(
        request=request,
        name="bracket.html",
        context={
            "bracket_matches": bracket_matches,
            "bracket_rounds": bracket_rounds,
            "final_results": final_results,
            "current_user": current_user,
        },
    )


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Health check endpoint to verify server responsiveness."""
    return {"status": "ok"}


@app.get("/api/bracket/live", tags=["tournament"])
def get_live_bracket(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return bracket pairings and their current boards for public scoreboards."""
    pairings = db.query(BracketMatch).order_by(BracketMatch.id.asc()).all()
    payload: list[dict[str, Any]] = []
    for pairing in pairings:
        game = (
            db.query(Match)
            .filter(Match.bracket_match_id == pairing.id)
            .order_by(Match.id.desc())
            .first()
        )
        moves: list[dict[str, Any]] = []
        if game is not None:
            try:
                moves = json.loads(game.live_moves or "[]")
            except (TypeError, json.JSONDecodeError):
                moves = []

        try:
            game_results = json.loads(pairing.game_results or "[]")
        except (TypeError, json.JSONDecodeError):
            game_results = []

        game_winner = None
        if game is not None and game.winner_id is not None:
            game_winner = (
                game.player1.username
                if game.winner_id == game.player1_id
                else game.player2.username
            )
        payload.append(
            {
                "id": pairing.id,
                "round_name": pairing.round_name,
                "match_index": pairing.match_index + 1,
                "player1": pairing.player1.username if pairing.player1 else "TBD",
                "player2": pairing.player2.username if pairing.player2 else "TBD",
                "score_p1": pairing.score_p1,
                "score_p2": pairing.score_p2,
                "status": pairing.status,
                "winner": pairing.winner.username if pairing.winner else None,
                "game_results": game_results,
                "current_game": {
                    "match_id": game.id,
                    "player1": game.player1.username,
                    "player2": game.player2.username,
                    "moves": moves,
                    "winner": game_winner,
                    "live": pairing.status == "running" and game.replay_path is None and game.win_reason is None,
                    "win_reason": game.win_reason,
                    "turns": len(moves),
                }
                if game is not None
                else None,
                "initial_board": create_initial_board() if game is not None else None,
            }
        )

    return {"pairings": payload}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
