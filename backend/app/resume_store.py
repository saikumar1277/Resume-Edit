"""Per-user resume rows in Postgres."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Resume


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(row: Resume) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "note": row.note or "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
        "document": row.document or {},
        "blocks": row.blocks or [],
    }


def _summary(row: Resume) -> dict[str, Any]:
    document = row.document or {}
    return {
        "id": str(row.id),
        "source_file": document.get("source_file", ""),
        "note": row.note or "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def save_new(db: Session, user_id: UUID, resume: dict[str, Any]) -> dict[str, Any]:
    row = Resume(
        id=uuid.uuid4(),
        user_id=user_id,
        note=resume.get("note") or "",
        document=resume.get("document") or {},
        blocks=resume.get("blocks") or [],
        updated_at=_now(),
    )
    db.add(row)
    db.flush()
    return _as_dict(row)


def load(db: Session, user_id: UUID, resume_id: str) -> dict[str, Any] | None:
    try:
        parsed = UUID(resume_id)
    except ValueError:
        return None
    row = db.scalar(
        select(Resume).where(Resume.id == parsed, Resume.user_id == user_id)
    )
    return _as_dict(row) if row else None


def update(
    db: Session, user_id: UUID, resume_id: str, resume: dict[str, Any]
) -> dict[str, Any] | None:
    try:
        parsed = UUID(resume_id)
    except ValueError:
        return None
    row = db.scalar(
        select(Resume).where(Resume.id == parsed, Resume.user_id == user_id)
    )
    if row is None:
        return None
    if "blocks" in resume:
        row.blocks = resume["blocks"]
    if "document" in resume:
        row.document = resume["document"]
    if "note" in resume:
        row.note = resume["note"] or ""
    row.updated_at = _now()
    db.flush()
    return _as_dict(row)


def delete(db: Session, user_id: UUID, resume_id: str) -> bool:
    try:
        parsed = UUID(resume_id)
    except ValueError:
        return False
    row = db.scalar(
        select(Resume).where(Resume.id == parsed, Resume.user_id == user_id)
    )
    if row is None:
        return False
    db.delete(row)
    return True


def search(db: Session, user_id: UUID, query: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.updated_at.desc())
    ).all()
    items = [_summary(row) for row in rows]
    needle = query.strip().lower()
    if not needle:
        return items
    return [item for item in items if needle in (item.get("note") or "").lower()]
