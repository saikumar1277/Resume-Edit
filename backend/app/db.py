"""SQLAlchemy engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .config import DATABASE_URL


def _connect_args(url: str) -> dict[str, str]:
    raw = url.replace("postgresql+psycopg://", "postgresql://", 1)
    host = (urlparse(raw).hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "postgres", "::1"}:
        return {}
    if "sslmode=" in url.lower():
        return {}
    return {"sslmode": "require"}


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_timeout=30,
    connect_args=_connect_args(DATABASE_URL),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_db() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def ensure_sweep_meta() -> None:
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO sweep_meta
                  (id, status, started_at, finished_at, duration_s, job_count,
                   error_sample, next_run_at, counts_json)
                VALUES (1, 'idle', NULL, NULL, NULL, 0, '[]', NULL, '{}')
                ON CONFLICT (id) DO NOTHING
                """
            )
        )
