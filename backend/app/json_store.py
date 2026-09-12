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
from pathlib import Path

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(exist_ok=True)


def save_new(resume: dict) -> dict:
    resume_id = str(uuid.uuid4())
    resume = {**resume, "id": resume_id}
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
    _write(resume_id, existing)
    return existing


def _write(resume_id: str, resume: dict) -> None:
    path = STORAGE_DIR / f"{resume_id}.json"
    path.write_text(json.dumps(resume, indent=2, ensure_ascii=False))
