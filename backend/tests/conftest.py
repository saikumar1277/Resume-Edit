from __future__ import annotations

import os

os.environ["APP_ENV"] = "development"
os.environ["JOBS_SWEEP_DISABLE"] = "1"
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://pageone:pageone@127.0.0.1:5433/pageone",
)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0")
os.environ["SECRET_KEY"] = "test-secret"
os.environ["RESEND_API_KEY"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["COOKIE_SECURE"] = "0"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import mail, redis_client
from app.db import engine
from app.main import app


@pytest.fixture
def client():
    mail.payloads.clear()
    mail.last_verify_url = None
    mail.last_reset_url = None
    with TestClient(app) as test_client:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE sessions, resumes, users CASCADE"))
        redis_client.get_redis().flushdb()
        yield test_client
        test_client.cookies.clear()
