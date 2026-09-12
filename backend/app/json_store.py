"""
Tiny file-based store: one JSON file per resume.

This is a stand-in for Postgres. The FastAPI routes talk to these
functions (save/load/update), not to the filesystem directly. Later we
can swap this file for a Postgres version without changing the routes.

Concept: this is a "repository" — a thin layer whose only job is
"persist this dict / load this dict". Routes stay focused on HTTP.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_new(resume: dict) -> dict:
    resume_id = str(uuid.uuid4())
    resume = {
        **resume,
        "id": resume_id,
        "note": resume.get("note") or "",
        "updated_at": _now(),
    }
    _write(resume_id, resume)
    return resume


def load(resume_id: str) -> dict | None:
    path = STORAGE_DIR / f"{resume_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def update(resume_id: str, resume: dict) -> dict | None:
    existing = load(resume_id)
    if existing is None:
        return None
    if "blocks" in resume:
        existing["blocks"] = resume["blocks"]
    if "document" in resume:
        existing["document"] = resume["document"]
    if "note" in resume:
        existing["note"] = resume["note"] or ""
    existing["updated_at"] = _now()
    _write(resume_id, existing)
    return existing


def delete(resume_id: str) -> bool:
    path = STORAGE_DIR / f"{resume_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True


def _summary(resume: dict) -> dict:
    document = resume.get("document") or {}
    return {
        "id": resume.get("id"),
        "source_file": document.get("source_file", ""),
        "note": resume.get("note") or "",
        "updated_at": resume.get("updated_at") or "",
    }


def list_summaries() -> list[dict]:
    items = []
    for path in STORAGE_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        items.append(_summary(data))
    items.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
    return items


def search(query: str) -> list[dict]:
    items = list_summaries()
    needle = query.strip().lower()
    if not needle:
        return items
    return [item for item in items if needle in (item.get("note") or "").lower()]


def _write(resume_id: str, resume: dict) -> None:
    path = STORAGE_DIR / f"{resume_id}.json"
    path.write_text(json.dumps(resume, indent=2, ensure_ascii=False))
