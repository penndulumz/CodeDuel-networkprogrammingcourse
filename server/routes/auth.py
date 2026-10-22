"""Authentication routes, session handling, and security dependencies."""

from __future__ import annotations

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from server.database import get_db
from server.models import AuthSession, User
from server.network import should_use_secure_cookie

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory session store mapping active token string to user ID
ACTIVE_SESSIONS: Dict[str, int] = {}
SESSION_TTL_SECONDS = 12 * 60 * 60


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_user_for_token(token: str | None, db: Session) -> User | None:
    """Resolve in-process test sessions and persistent browser sessions."""
    if not token:
        return None
    session = db.query(AuthSession).filter(AuthSession.token_hash == _token_hash(token)).first()
    if session:
        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            db.delete(session)
            db.commit()
            ACTIVE_SESSIONS.pop(token, None)
            return None
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user:
            db.delete(session)
            db.commit()
            ACTIVE_SESSIONS.pop(token, None)
            return None
        return user

    # Retain compatibility with tests and integrations that inject an
    # in-process session directly instead of authenticating through /login.
    user_id = ACTIVE_SESSIONS.get(token)
    return db.query(User).filter(User.id == user_id).first() if user_id is not None else None


class RegisterRequest(BaseModel):
    """Pydantic schema for user account registration."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


def get_token_from_request(request: Request) -> str | None:
    """Extract session token from Authorization header or HTTP cookies."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return request.cookies.get("session_token")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Dependency that resolves the authenticated User from the active session."""
    user = get_user_for_token(get_token_from_request(request), db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that ensures the authenticated User has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Register a new user account with unique username and hashed password."""
    username = payload.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty",
        )

    target_admin = os.getenv("ADMIN_USERNAME", "admin").strip().lower()
    if username.lower() == target_admin or username.lower() == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is reserved for administrator",
        )

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(username=username, elo=1200)
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "elo": user.elo,
        "is_admin": user.is_admin,
    }


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Authenticate user credentials from JSON or form data, issuing a session token."""
    content_type = request.headers.get("content-type", "")
    username: str | None = None
    password: str | None = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed JSON body",
            )
    else:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed form data",
            )

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both username and password are required",
        )

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = secrets.token_hex(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)
    db.add(AuthSession(
        token_hash=_token_hash(token),
        user_id=user.id,
        expires_at=expires_at.replace(tzinfo=None),
    ))
    db.commit()
    ACTIVE_SESSIONS[token] = user.id

    # Secure flag follows COOKIE_SECURE, or the request scheme when unset (auto)
    secure_cookie = should_use_secure_cookie(request)

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        path="/",
        max_age=SESSION_TTL_SECONDS,
    )
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "elo": user.elo,
            "is_admin": user.is_admin,
        },
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """Terminate the active session and clear session cookie."""
    token = get_token_from_request(request)
    if token:
        ACTIVE_SESSIONS.pop(token, None)
        session = db.query(AuthSession).filter(AuthSession.token_hash == _token_hash(token)).first()
        if session:
            db.delete(session)
            db.commit()

    # Secure flag follows COOKIE_SECURE, or the request scheme when unset (auto)
    secure_cookie = should_use_secure_cookie(request)

    response.delete_cookie(
        key="session_token",
        path="/",
        secure=secure_cookie,
        httponly=True,
        samesite="lax",
    )
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve profile and statistics for the currently authenticated user."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "elo": current_user.elo,
        "is_admin": current_user.is_admin,
        "wins": current_user.wins,
        "losses": current_user.losses,
        "draws": current_user.draws,
    }
