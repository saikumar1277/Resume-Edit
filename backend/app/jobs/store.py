"""Postgres snapshot for instant job search. Publish only after a sweep finishes."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from ..db import ensure_sweep_meta, session_scope
from ..models import JobStaging
from .normalize import experience_level, to_job

STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
STALE_DAYS = 30

_COLUMNS = (
    "id",
    "url",
    "title",
    "company",
    "location",
    "workplace",
    "type",
    "posted_at",
    "tags",
    "provider",
    "experience",
    "first_seen",
    "scraped_at",
)
_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9_+-]+")
_POSTED_DAYS = {"1d": 1, "7d": 7, "30d": 30}
_SORT_SQL = {
    "posted_desc": "jobs.posted_at DESC, lower(jobs.company)",
    "posted_asc": "jobs.posted_at ASC, lower(jobs.company)",
    "company": "lower(jobs.company), jobs.posted_at DESC",
    "title": "lower(jobs.title), jobs.posted_at DESC",
}

_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


def init() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_sweep_meta()


def job_count() -> int:
    with session_scope() as session:
        row = session.execute(text("SELECT COUNT(*) AS n FROM jobs")).mappings().one()
        return int(row["n"] or 0)


def staging_count() -> int:
    with session_scope() as session:
        row = (
            session.execute(text("SELECT COUNT(*) AS n FROM jobs_staging"))
            .mappings()
            .one()
        )
        return int(row["n"] or 0)


def get_meta() -> dict[str, Any]:
    with session_scope() as session:
        row = (
            session.execute(text("SELECT * FROM sweep_meta WHERE id = 1"))
            .mappings()
            .first()
        )
    if row is None:
        return {
            "status": "idle",
            "started_at": None,
            "finished_at": None,
            "duration_s": None,
            "job_count": 0,
            "error_sample": [],
            "next_run_at": None,
            "counts": {},
        }
    try:
        errors = json.loads(row["error_sample"] or "[]")
    except json.JSONDecodeError:
        errors = []
    try:
        counts = json.loads(row["counts_json"] or "{}")
    except json.JSONDecodeError:
        counts = {}
    return {
        "status": row["status"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "duration_s": row["duration_s"],
        "job_count": row["job_count"] or 0,
        "error_sample": errors if isinstance(errors, list) else [],
        "next_run_at": row["next_run_at"],
        "counts": counts if isinstance(counts, dict) else {},
    }


def set_next_run_at(when: str | None) -> None:
    with session_scope() as session:
        session.execute(
            text("UPDATE sweep_meta SET next_run_at = :when WHERE id = 1"),
            {"when": when},
        )


def mark_stale_running_failed() -> None:
    with session_scope() as session:
        row = (
            session.execute(
                text("SELECT status FROM sweep_meta WHERE id = 1")
            )
            .mappings()
            .first()
        )
        if not row or row["status"] != "running":
            return
        session.execute(
            text(
                """
                UPDATE sweep_meta
                SET status = 'failed',
                    finished_at = :finished,
                    error_sample = :errors
                WHERE id = 1
                """
            ),
            {
                "finished": _now_iso(),
                "errors": json.dumps(["sweep interrupted"]),
            },
        )
        session.execute(text("DELETE FROM jobs_staging"))


def begin_ingest() -> str:
    started = _now_iso()
    with session_scope() as session:
        session.execute(text("DELETE FROM jobs_staging"))
        session.execute(
            text(
                """
                UPDATE sweep_meta
                SET status = 'running',
                    started_at = :started,
                    finished_at = NULL,
                    duration_s = NULL,
                    error_sample = '[]',
                    counts_json = '{}'
                WHERE id = 1
                """
            ),
            {"started": started},
        )
    return started


def insert_jobs(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    values = []
    for row in rows:
        stored = _to_stored(row)
        if stored is None:
            continue
        values.append(stored)
    if not values:
        return 0
    stmt = insert(JobStaging).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={col: getattr(stmt.excluded, col) for col in _COLUMNS if col != "id"},
    )
    with _lock:
        with session_scope() as session:
            session.execute(stmt)
    return len(values)


def publish(
    *,
    started_at: str,
    errors: list[str],
    counts: dict[str, int],
    interval_s: float,
) -> int:
    finished = _now()
    finished_iso = finished.isoformat().replace("+00:00", "Z")
    cutoff = (finished - timedelta(days=STALE_DAYS)).isoformat().replace("+00:00", "Z")
    next_run = (finished + timedelta(seconds=interval_s)).isoformat().replace(
        "+00:00", "Z"
    )
    duration = None
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        duration = (finished - start).total_seconds()
    except ValueError:
        duration = None

    cols = ", ".join(_COLUMNS)
    with session_scope() as session:
        session.execute(
            text(
                """
                UPDATE jobs_staging AS staging
                SET first_seen = COALESCE(
                  (SELECT jobs.first_seen FROM jobs WHERE jobs.url = staging.url),
                  staging.first_seen
                )
                """
            )
        )
        session.execute(
            text(
                f"""
                INSERT INTO jobs_staging ({cols})
                SELECT {cols} FROM jobs
                WHERE scraped_at >= :cutoff
                  AND url NOT IN (SELECT url FROM jobs_staging)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"cutoff": cutoff},
        )
        session.execute(text("DELETE FROM jobs"))
        session.execute(
            text(f"INSERT INTO jobs ({cols}) SELECT {cols} FROM jobs_staging")
        )
        session.execute(text("DELETE FROM jobs_staging"))
        count = session.execute(text("SELECT COUNT(*) AS n FROM jobs")).mappings().one()[
            "n"
        ]
        session.execute(
            text(
                """
                UPDATE sweep_meta
                SET status = 'idle',
                    finished_at = :finished,
                    duration_s = :duration,
                    job_count = :count,
                    error_sample = :errors,
                    next_run_at = :next_run,
                    counts_json = :counts
                WHERE id = 1
                """
            ),
            {
                "finished": finished_iso,
                "duration": duration,
                "count": int(count),
                "errors": json.dumps(errors[:20]),
                "next_run": next_run,
                "counts": json.dumps(counts),
            },
        )
        return int(count)


def abort(reason: str) -> None:
    with session_scope() as session:
        session.execute(text("DELETE FROM jobs_staging"))
        session.execute(
            text(
                """
                UPDATE sweep_meta
                SET status = 'failed',
                    finished_at = :finished,
                    error_sample = :errors
                WHERE id = 1
                """
            ),
            {"finished": _now_iso(), "errors": json.dumps([reason])},
        )


def load_dead_slugs(provider: str) -> set[str]:
    with session_scope() as session:
        rows = session.execute(
            text("SELECT slug FROM dead_slugs WHERE provider = :provider"),
            {"provider": provider},
        ).mappings()
        return {str(row["slug"]) for row in rows}


def add_dead_slugs(provider: str, slugs: dict[str, int | None]) -> None:
    if not slugs:
        return
    seen = _now_iso()
    values = [
        {
            "provider": provider,
            "slug": slug,
            "status": status,
            "seen_at": seen,
        }
        for slug, status in slugs.items()
    ]
    from ..models import DeadSlug

    stmt = insert(DeadSlug).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["provider", "slug"],
        set_={
            "status": stmt.excluded.status,
            "seen_at": stmt.excluded.seen_at,
        },
    )
    with session_scope() as session:
        session.execute(stmt)


def search(
    *,
    title: str = "",
    location: str = "",
    company: str = "",
    workplaces: list[str] | None = None,
    job_types: list[str] | None = None,
    experience: list[str] | None = None,
    posted: str = "",
    exclude: str = "",
    sort: str = "posted_desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    match = _title_match(title)
    if match:
        where.append("jobs.title_tsv @@ to_tsquery('simple', :title_q)")
        params["title_q"] = match
    elif title.strip():
        where.append("jobs.title ILIKE :title_like")
        params["title_like"] = f"%{title.strip()}%"
    if location.strip():
        where.append("jobs.location ILIKE :location")
        params["location"] = f"%{location.strip()}%"
    if company.strip():
        where.append("jobs.company ILIKE :company")
        params["company"] = f"%{company.strip()}%"
    if workplaces:
        keys = []
        for index, value in enumerate(workplaces):
            key = f"workplace_{index}"
            keys.append(f":{key}")
            params[key] = value
        where.append(f"jobs.workplace IN ({', '.join(keys)})")
    if job_types:
        keys = []
        for index, value in enumerate(job_types):
            key = f"type_{index}"
            keys.append(f":{key}")
            params[key] = value
        where.append(f"jobs.type IN ({', '.join(keys)})")
    if experience:
        keys = []
        for index, value in enumerate(experience):
            key = f"experience_{index}"
            keys.append(f":{key}")
            params[key] = value
        where.append(f"jobs.experience IN ({', '.join(keys)})")
    days = _POSTED_DAYS.get(posted)
    if days:
        cutoff = (_now().date() - timedelta(days=days)).isoformat()
        where.append("jobs.posted_at != '' AND jobs.posted_at >= :posted_cutoff")
        params["posted_cutoff"] = cutoff
    exclude_parts = [
        part.lower()
        for part in re.split(r"[\s,]+", exclude.strip())
        if part
    ]
    for index, token in enumerate(exclude_parts):
        key = f"exclude_{index}"
        where.append(
            f"strpos(lower(jobs.title), :{key}) = 0 "
            f"AND strpos(lower(jobs.company), :{key}) = 0"
        )
        params[key] = token
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    order = _SORT_SQL.get(sort, _SORT_SQL["posted_desc"])
    count_sql = f"SELECT COUNT(*) AS n FROM jobs {clause}"
    list_sql = (
        f"SELECT jobs.id, jobs.url, jobs.title, jobs.company, jobs.location, "
        f"jobs.workplace, jobs.type, jobs.posted_at, jobs.tags, jobs.experience "
        f"FROM jobs {clause} ORDER BY {order} LIMIT :limit OFFSET :offset"
    )
    with session_scope() as session:
        total = int(session.execute(text(count_sql), params).mappings().one()["n"])
        rows = session.execute(text(list_sql), params).mappings().all()
    return [_row_to_job(row) for row in rows], total


def _title_match(title: str) -> str | None:
    tokens = _FTS_TOKEN_RE.findall(title.strip())[:8]
    if not tokens:
        return None
    return " & ".join(f"{token}:*" for token in tokens)


def _to_stored(raw: dict[str, Any]) -> dict[str, Any] | None:
    job = to_job({**raw, "description": ""})
    if job is None:
        return None
    scraped = str(raw.get("scraped_at") or _now_iso())
    return {
        "id": job["id"],
        "url": job["url"],
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "workplace": job["workplace"],
        "type": job["type"],
        "posted_at": job.get("postedAt") or "",
        "tags": json.dumps(job.get("tags") or []),
        "provider": str(raw.get("provider") or ""),
        "experience": job.get("experience") or experience_level(job["title"]),
        "first_seen": str(raw.get("first_seen") or scraped),
        "scraped_at": scraped,
    }


def _row_to_job(row: Any) -> dict[str, Any]:
    try:
        tags = json.loads(row["tags"] or "[]")
    except (json.JSONDecodeError, TypeError):
        tags = []
    if not isinstance(tags, list):
        tags = []
    return {
        "id": row["id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "workplace": row["workplace"],
        "type": row["type"],
        "postedAt": row["posted_at"],
        "description": "",
        "tags": [str(tag) for tag in tags if str(tag).strip()],
        "url": row["url"],
        "experience": row["experience"] or experience_level(row["title"]),
    }
