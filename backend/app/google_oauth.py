"""Google authorization-code login. Optional when keys are missing."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, redis_client
from .config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_ENABLED,
    OAUTH_STATE_TTL_S,
    APP_PUBLIC_URL,
)
from .models import User

log = logging.getLogger(__name__)

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


class GoogleDisabledError(RuntimeError):
    pass


class GoogleAuthError(RuntimeError):
    pass


def redirect_uri() -> str:
    return f"{APP_PUBLIC_URL}/api/auth/google/callback"


def authorization_url(next_path: str = "") -> str:
    if not GOOGLE_ENABLED:
        raise GoogleDisabledError("Google sign-in is not configured.")
    import secrets

    state = secrets.token_urlsafe(24)
    redis_client.put_json(
        "oauth",
        state,
        {"next": auth.safe_next_path(next_path)},
        OAUTH_STATE_TTL_S,
    )
    query = urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "prompt": "select_account",
        }
    )
    return f"{AUTH_URL}?{query}"


def fetch_google_profile(code: str) -> dict:
    with httpx.Client(timeout=15.0) as client:
        token_res = client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
        try:
            token_res.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleAuthError("token exchange failed") from exc
        access = token_res.json().get("access_token")
        if not access:
            raise GoogleAuthError("token exchange failed")
        user_res = client.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access}"},
        )
        try:
            user_res.raise_for_status()
        except httpx.HTTPError as exc:
            raise GoogleAuthError("userinfo failed") from exc
        data = user_res.json()
        if not isinstance(data, dict):
            raise GoogleAuthError("userinfo failed")
        return data


def finish(db: Session, code: str, state: str) -> tuple[User, str]:
    payload = redis_client.take_json("oauth", state)
    if not payload:
        raise GoogleAuthError("invalid oauth state")
    next_path = auth.safe_next_path(str(payload.get("next") or ""))
    profile = fetch_google_profile(code)
    email = auth.normalize_email(str(profile.get("email") or ""))
    sub = str(profile.get("id") or profile.get("sub") or "").strip()
    verified = bool(profile.get("verified_email") or profile.get("email_verified"))
    if not email or not sub:
        raise GoogleAuthError("google profile missing email")
    if not verified:
        raise GoogleAuthError("google email is not verified")

    user = db.scalar(select(User).where(User.google_sub == sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == email))
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            email=email,
            password_hash=None,
            google_sub=sub,
            email_verified_at=now,
        )
        db.add(user)
        db.flush()
        log.info("google created user")
    else:
        if user.google_sub and user.google_sub != sub:
            raise GoogleAuthError("google account mismatch")
        user.google_sub = sub
        if user.email_verified_at is None:
            user.email_verified_at = now
        db.flush()
        log.info("google linked user")
    return user, next_path
