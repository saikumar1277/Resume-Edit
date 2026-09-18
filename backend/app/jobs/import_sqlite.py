"""Copy a local SQLite jobs.db snapshot into Postgres once."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from app.db import session_scope
from app.jobs.store import STORAGE_DIR, _COLUMNS, init
from app.models import DeadSlug

SQLITE_PATH = STORAGE_DIR / "jobs.db"
BATCH = 1000


def _sqlite() -> sqlite3.Connection:
    if not SQLITE_PATH.exists():
        raise SystemExit(f"No SQLite snapshot at {SQLITE_PATH}")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def import_jobs(*, force: bool = False) -> dict[str, int]:
    init()
    with session_scope() as session:
        count = int(
            session.execute(text("SELECT COUNT(*) AS n FROM jobs")).mappings().one()["n"]
        )
        if count > 0 and not force:
            return {"skipped": count, "jobs": 0, "dead_slugs": 0}

    source = _sqlite()
    inserted = 0
    cols = list(source.execute("PRAGMA table_info(jobs)").fetchall())
    names = {str(col[1]) for col in cols}
    select_cols = ", ".join(_COLUMNS)
    if "experience" not in names:
        select_sql = (
            "SELECT id, url, title, company, location, workplace, type, "
            "posted_at, tags, provider, 'mid' AS experience, first_seen, scraped_at "
            "FROM jobs"
        )
    else:
        select_sql = f"SELECT {select_cols} FROM jobs"

    batch: list[dict] = []
    for row in source.execute(select_sql):
        batch.append({col: row[col] for col in _COLUMNS})
        if len(batch) >= BATCH:
            _upsert_jobs(batch)
            inserted += len(batch)
            batch = []
    if batch:
        _upsert_jobs(batch)
        inserted += len(batch)

    dead = 0
    try:
        dead_rows = source.execute(
            "SELECT provider, slug, status, seen_at FROM dead_slugs"
        ).fetchall()
    except sqlite3.OperationalError:
        dead_rows = []
    if dead_rows:
        values = [
            {
                "provider": row["provider"],
                "slug": row["slug"],
                "status": row["status"],
                "seen_at": row["seen_at"],
            }
            for row in dead_rows
        ]
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
        dead = len(values)

    try:
        meta = source.execute("SELECT * FROM sweep_meta WHERE id = 1").fetchone()
    except sqlite3.OperationalError:
        meta = None
    if meta is not None:
        with session_scope() as session:
            session.execute(
                text(
                    """
                    UPDATE sweep_meta
                    SET status = :status,
                        started_at = :started_at,
                        finished_at = :finished_at,
                        duration_s = :duration_s,
                        job_count = :job_count,
                        error_sample = :error_sample,
                        next_run_at = :next_run_at,
                        counts_json = :counts_json
                    WHERE id = 1
                    """
                ),
                {
                    "status": meta["status"] or "idle",
                    "started_at": meta["started_at"],
                    "finished_at": meta["finished_at"],
                    "duration_s": meta["duration_s"],
                    "job_count": meta["job_count"] or inserted,
                    "error_sample": meta["error_sample"] or "[]",
                    "next_run_at": meta["next_run_at"],
                    "counts_json": meta["counts_json"] or "{}",
                },
            )
    source.close()
    return {"skipped": 0, "jobs": inserted, "dead_slugs": dead}


def _upsert_jobs(values: list[dict]) -> None:
    cols = ", ".join(_COLUMNS)
    placeholders = ", ".join(f":{col}" for col in _COLUMNS)
    updates = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in _COLUMNS if col != "id"
    )
    sql = text(
        f"""
        INSERT INTO jobs ({cols})
        VALUES ({placeholders})
        ON CONFLICT (id) DO UPDATE SET {updates}
        """
    )
    with session_scope() as session:
        session.execute(sql, values)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import jobs.db into Postgres.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Import even if Postgres already has jobs.",
    )
    args = parser.parse_args(argv)
    result = import_jobs(force=args.force)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
