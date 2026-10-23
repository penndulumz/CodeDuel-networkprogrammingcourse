"""FastAPI application entrypoint for Battlecode 9x9 RPS Platform.

Configures CORS, database initialization lifecycle, mounts all REST API routes
for authentication, bot management, match challenges, leaderboard rankings, and
tournament administration, and serves static files and Jinja2 web UI templates.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from engine.games import GAMES, is_grid_game, list_games
from server.database import get_db, init_db
from server.bracket import get_final_results, get_round_size, is_bracket_finished
from server.games import get_active_game, get_catalog_games
from server.models import Bot, BracketMatch, Match, User
from server.network import get_public_url
from server.routes import admin, auth, bots, grade, leaderboard, matches
from server.routes.admin import _get_all_settings_dict
from server.routes.auth import get_token_from_request, get_user_for_token
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

# Compress HTML/JSON/JS responses. Replays and pages shrink 5-10x, which matters
# most for players on slow WAN links or a shared classroom Wi-Fi.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Mount static files for web UI
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates configuration
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Game metadata is needed on almost every page (navbar, cards, badges).
templates.env.globals["games_list"] = [GAMES["rps9x9"]]
templates.env.globals["games_map"] = GAMES

# Mount all feature routes under /api
app.include_router(auth.router, prefix="/api")
app.include_router(bots.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(grade.router, prefix="/api")


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
    return get_user_for_token(get_token_from_request(request), db)


# ================== WEB UI HTML ROUTES ==================


@app.get("/", response_class=HTMLResponse, tags=["web"])
def home_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the landing page: what the platform is, the games and how to start."""
    current_user = _get_optional_user(request, db)
    active_game = get_active_game(db)
    players = db.query(User).filter(User.is_admin == False)  # noqa: E712
    top_players = (
        players.order_by(User.elo.desc(), User.wins.desc(), User.id.asc()).limit(5).all()
    )
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "games_list": get_catalog_games(db), "current_user": current_user,
            "active_game": GAMES[active_game],
            "top_players": top_players,
            "stats": {
                "players": players.count(),
                "bots": db.query(Bot).count(),
                "matches": db.query(Match).count(),
                "games": len(get_catalog_games(db)),
            },
            "is_portal_open": _is_portal_open_now(db),
            "public_url": get_public_url(request),
        },
    )


@app.get("/leaderboard", response_class=HTMLResponse, tags=["web"])
def leaderboard_page(
    request: Request,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Render the leaderboard and FFA challenge portal."""
    current_user = _get_optional_user(request, db)
    active_game = get_active_game(db)
    users = (
        db.query(User)
        .order_by(User.elo.desc(), User.wins.desc(), User.id.asc())
        .all()
    )

    ranking_list: List[Dict[str, Any]] = []
    for rank_idx, u in enumerate(users, start=1):
        has_active = any(b.is_active and b.game_type == active_game for b in u.bots)
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
            "games_list": get_catalog_games(db), "current_user": current_user,
            "active_game": GAMES[active_game],
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
        context={"games_list": get_catalog_games(db), "current_user": current_user},
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
        context={"games_list": get_catalog_games(db), "current_user": current_user},
    )


@app.get("/profile", response_class=HTMLResponse, tags=["web"])
def profile_page(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    """Render the user profile, bot upload drop zone, and match history page."""
    current_user = _get_optional_user(request, db)
    user_bots: List[Bot] = []
    user_matches: List[Match] = []
    page_size = 10
    total_matches = 0
    total_pages = 1

    if current_user:
        user_bots = (
            db.query(Bot)
            .filter(Bot.user_id == current_user.id, Bot.is_deleted == False)  # noqa: E712
            .order_by(Bot.uploaded_at.desc())
            .all()
        )
        match_query = (
            db.query(Match)
            .filter(or_(Match.player1_id == current_user.id, Match.player2_id == current_user.id))
        )
        total_matches = match_query.count()
        total_pages = max(1, (total_matches + page_size - 1) // page_size)
        page = min(page, total_pages)
        user_matches = (
            match_query.order_by(Match.created_at.desc(), Match.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "active_game": GAMES[get_active_game(db)],
            "games_list": get_catalog_games(db), "current_user": current_user,
            "user_bots": user_bots,
            "user_matches": user_matches,
            "history_page": page,
            "history_total_pages": total_pages,
            "history_total": total_matches,
            "history_start": (page - 1) * page_size + 1 if total_matches else 0,
            "history_end": min(page * page_size, total_matches),
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
    game_type = getattr(match, "game_type", None) or "rps9x9"
    return templates.TemplateResponse(
        request=request,
        name="replay_grid.html" if is_grid_game(game_type) else "replay.html",
        context={
            "match_id": match_id,
            "match": match,
            "games_list": get_catalog_games(db), "current_user": current_user,
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
            "games_list": get_catalog_games(db), "current_user": current_user,
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
    bracket_rounds = sorted(present_rounds, key=get_round_size, reverse=True)
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
            "games_list": get_catalog_games(db), "current_user": current_user,
        },
    )


@app.get("/games", response_class=HTMLResponse, tags=["web"])
def games_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """List every game with its difficulty, board and move format."""
    return templates.TemplateResponse(
        request=request,
        name="games.html",
        context={
            "games_list": get_catalog_games(db), "current_user": _get_optional_user(request, db),
            "active_game": GAMES[get_active_game(db)],
        },
    )


# Starter files shown on each game page, read from disk so the page and the
# downloadable kit can never drift apart.
GAME_TEMPLATE_FILES: Dict[str, str] = {
    "connect4": "connect4_template.py",
    "caro": "caro_template.py",
    "rps9x9": "bot_template.py",
}


@app.get("/games/{slug}", response_class=HTMLResponse, tags=["web"])
def game_detail_page(slug: str, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Render the rules, bot interface and starter code for one game."""
    if slug not in GAMES:
        raise HTTPException(status_code=404, detail="Game not found")
    template_path = BASE_DIR / "starter_kit" / GAME_TEMPLATE_FILES[slug]
    return templates.TemplateResponse(
        request=request,
        name="game_detail.html",
        context={
            "games_list": get_catalog_games(db), "current_user": _get_optional_user(request, db),
            "game": GAMES[slug],
            "active_game": GAMES[get_active_game(db)],
            "template_file": GAME_TEMPLATE_FILES[slug],
            "template_code": template_path.read_text(encoding="utf-8"),
        },
    )


@app.get("/play/{slug}", response_class=HTMLResponse, tags=["web"])
def play_page(slug: str, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Play a game against the computer directly in the browser."""
    if slug not in GAMES:
        raise HTTPException(status_code=404, detail="Game not found")
    return templates.TemplateResponse(
        request=request,
        name="play.html",
        context={"games_list": get_catalog_games(db), "current_user": _get_optional_user(request, db), "game": GAMES[slug]},
    )


@app.get("/guide", response_class=HTMLResponse, tags=["web"])
def guide_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Step-by-step guide for new players (first-year students)."""
    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context={
            "games_list": get_catalog_games(db), "current_user": _get_optional_user(request, db),
            "active_game": GAMES[get_active_game(db)],
        },
    )


@app.get("/guide/organizer", response_class=HTMLResponse, tags=["web"])
def organizer_guide_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Guide for organisers: offline LAN events, WAN access and grading."""
    return templates.TemplateResponse(
        request=request,
        name="organizer.html",
        context={
            "games_list": get_catalog_games(db), "current_user": _get_optional_user(request, db),
            "public_url": get_public_url(request),
        },
    )


@app.get("/grade", response_class=HTMLResponse, tags=["web"])
def grade_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """Self-grading page: run a bot against the reference ladder for a score."""
    return templates.TemplateResponse(
        request=request,
        name="grade.html",
        context={
            "games_list": get_catalog_games(db), "current_user": _get_optional_user(request, db),
            "active_game": GAMES[get_active_game(db)],
        },
    )


# Paths bundled into the offline starter kit: enough to write, test and grade
# bots for every game without the server or an internet connection.
STARTER_KIT_PATHS = ["starter_kit", "engine", "server/bosses", "docs/BOT_GUIDE.md"]

OFFLINE_KIT_README = """CodeDuel - bo cong cu offline
==============================
Yeu cau: Python 3.10+ (khong can cai them thu vien nao).

1. Giai nen, mo terminal trong thu muc codeduel-kit.
2. Chon game va sua file mau:
     starter_kit/connect4_template.py   (Connect Four - de nhat)
     starter_kit/caro_template.py       (Caro 15x15)
     starter_kit/bot_template.py        (RPS Chess 9x9)
3. Cho 2 bot dau voi nhau:
     python starter_kit/local_arena.py starter_kit/connect4_template.py starter_kit/connect4_bot.py --game connect4 -v
4. Tu cham diem (thang 10):
     python starter_kit/grade.py starter_kit/connect4_template.py --game connect4
5. Giao vien cham ca lop (moi bot mot file .py trong thu muc bai_nop):
     python starter_kit/grade.py bai_nop --game connect4 --csv diem.csv
6. Khi khong co mang, tao goi nop de luu tren may:
     python starter_kit/pack_submission.py duong_dan/bot.py --game rps9x9
   Giu file .cdsubmit.zip trong thu muc submissions. Khi co ket noi lai,
   dang nhap CodeDuel, mo Ho so va tai goi nay len. Chi bien nhan tu may chu
   moi xac nhan bai da duoc nop; thoi gian trong goi offline khong phai moc
   thoi gian chinh thuc cua giai.
"""


def build_starter_kit_zip() -> bytes:
    """Zip the offline toolkit (starter bots, engine, grader, reference bosses)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel in STARTER_KIT_PATHS:
            source = BASE_DIR / rel
            files = [source] if source.is_file() else sorted(source.rglob("*.py"))
            for file in files:
                if "__pycache__" in file.parts:
                    continue
                archive.write(file, f"codeduel-kit/{file.relative_to(BASE_DIR).as_posix()}")
        archive.writestr("codeduel-kit/server/__init__.py", "")
        archive.writestr("codeduel-kit/README.txt", OFFLINE_KIT_README)
    return buffer.getvalue()


@app.get("/download/starter-kit.zip", tags=["web"])
def download_starter_kit() -> Response:
    """Download the offline toolkit (works with no server or internet afterwards)."""
    return Response(
        content=build_starter_kit_zip(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="codeduel-starter-kit.zip"'},
    )


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Health check endpoint to verify server responsiveness."""
    return {"status": "ok"}


@app.get("/api/bracket/live", tags=["tournament"])
def get_live_bracket(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return bracket pairings and their current boards for public scoreboards."""
    pairings = (
        db.query(BracketMatch)
        .options(
            selectinload(BracketMatch.player1),
            selectinload(BracketMatch.player2),
            selectinload(BracketMatch.winner),
        )
        .order_by(BracketMatch.id.asc())
        .all()
    )
    pairing_ids = [pairing.id for pairing in pairings]
    games_by_pairing: Dict[int, list[Match]] = {}
    if pairing_ids:
        games = (
            db.query(Match)
            .options(selectinload(Match.player1), selectinload(Match.player2))
            .filter(Match.bracket_match_id.in_(pairing_ids))
            .order_by(Match.id.asc())
            .all()
        )
        for game in games:
            if game.bracket_match_id is not None:
                games_by_pairing.setdefault(game.bracket_match_id, []).append(game)
    payload: list[dict[str, Any]] = []
    for pairing in pairings:
        series_games = games_by_pairing.get(pairing.id, [])
        game = series_games[-1] if series_games else None
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
                "is_bye": pairing.player1_id is None or pairing.player2_id is None,
                "score_p1": pairing.score_p1,
                "score_p2": pairing.score_p2,
                "status": pairing.status,
                "winner": pairing.winner.username if pairing.winner else None,
                "winner_player": (
                    1 if pairing.winner_id == pairing.player1_id else 2
                ) if pairing.winner_id is not None else None,
                "game_results": game_results,
                "games": [
                    {
                        "match_id": series_game.id,
                        "game_number": game_number,
                        "winner": (
                            pairing.player1.username
                            if series_game.winner_id == pairing.player1_id and pairing.player1
                            else pairing.player2.username
                            if series_game.winner_id == pairing.player2_id and pairing.player2
                            else None
                        ),
                        "win_reason": series_game.win_reason,
                        "turns": series_game.total_turns,
                        "has_replay": bool(series_game.replay_path),
                    }
                    for game_number, series_game in enumerate(series_games, start=1)
                ],
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
