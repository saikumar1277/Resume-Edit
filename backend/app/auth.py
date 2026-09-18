"""Email/password sessions stored in Postgres, sent as an httpOnly cookie."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import COOKIE_SECURE, SESSION_COOKIE, SESSION_DAYS
from .db import get_db
from .models import AuthSession, User

log = logging.getLogger(__name__)
_hasher = PasswordHasher()
_COOKIE_SAMESITE = "lax"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        _hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def safe_next_path(raw: str | None) -> str:
    if raw and raw.startswith("/") and not raw.startswith("//"):
        return raw
    return "/resumes"


def create_session(db: Session, user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user_id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
        )
    )
    db.flush()
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite=_COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
        max_age=SESSION_DAYS * 86400,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite=_COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
    )


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in.",
        )
    session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    if session is None or session.expires_at <= datetime.now(timezone.utc):
        if session is not None:
            db.delete(session)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in.",
        )
    user = db.get(User, session.user_id)
    if user is None:
        db.delete(session)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not signed in.",
        )
    return user


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    if session is not None:
        db.delete(session)


def revoke_sessions_for_user(db: Session, user_id: UUID) -> None:
    sessions = db.scalars(
        select(AuthSession).where(AuthSession.user_id == user_id)
    ).all()
    for session in sessions:
        db.delete(session)
