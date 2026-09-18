"""Runtime settings from the environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://pageone:pageone@127.0.0.1:5433/pageone"
)
_DEFAULT_REDIS_URL = "redis://127.0.0.1:6379/0"
_WEAK_SECRETS = {
    "",
    "dev-secret-change-me",
    "change-me-in-production",
    "compose-dev-secret-not-for-prod",
}

APP_ENV = os.environ.get("APP_ENV", "development").strip().lower() or "development"
IS_PRODUCTION = APP_ENV == "production"


def _sqlalchemy_url(raw: str) -> str:
    url = raw.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required when APP_ENV=production")
    return value


if IS_PRODUCTION:
    DATABASE_URL = _sqlalchemy_url(_require("DATABASE_URL"))
    SECRET_KEY = _require("SECRET_KEY")
    if SECRET_KEY in _WEAK_SECRETS:
        raise RuntimeError("SECRET_KEY must be a strong value in production")
    REDIS_URL = _require("REDIS_URL")
else:
    DATABASE_URL = _sqlalchemy_url(
        os.environ.get("DATABASE_URL", _DEFAULT_DATABASE_URL)
    )
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    REDIS_URL = (
        os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL).strip() or _DEFAULT_REDIS_URL
    )

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Page one <noreply@localhost>").strip()

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
APP_PUBLIC_URL = os.environ.get("APP_PUBLIC_URL", "http://localhost:3000").rstrip("/")
if APP_PUBLIC_URL and APP_PUBLIC_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(APP_PUBLIC_URL)

_cookie_raw = os.environ.get("COOKIE_SECURE")
if _cookie_raw is None or _cookie_raw.strip() == "":
    COOKIE_SECURE = IS_PRODUCTION
else:
    COOKIE_SECURE = _cookie_raw.strip().lower() in {"1", "true", "yes"}

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

SESSION_COOKIE = "session"
SESSION_DAYS = 30
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
VERIFY_TTL_S = 24 * 3600
RESET_TTL_S = 3600
OAUTH_STATE_TTL_S = 600
