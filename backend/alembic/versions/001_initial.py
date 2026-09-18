"""initial postgres schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE TABLE users (
          id UUID PRIMARY KEY,
          email VARCHAR(320) NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX users_email_idx ON users (email)")
    op.execute(
        """
        CREATE TABLE sessions (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          token_hash VARCHAR(64) NOT NULL UNIQUE,
          expires_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX sessions_user_id_idx ON sessions (user_id)")
    op.execute("CREATE INDEX sessions_token_hash_idx ON sessions (token_hash)")
    op.execute(
        """
        CREATE TABLE resumes (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          note TEXT NOT NULL DEFAULT '',
          document JSONB NOT NULL,
          blocks JSONB NOT NULL,
          updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX resumes_user_id_idx ON resumes (user_id)")
    op.execute(
        "CREATE INDEX resumes_user_updated_idx ON resumes (user_id, updated_at DESC)"
    )
    op.execute(
        """
        CREATE TABLE jobs (
          id TEXT PRIMARY KEY,
          url TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          company TEXT NOT NULL,
          location TEXT NOT NULL,
          workplace TEXT NOT NULL,
          type TEXT NOT NULL,
          posted_at TEXT NOT NULL,
          tags TEXT NOT NULL,
          provider TEXT NOT NULL,
          experience TEXT NOT NULL DEFAULT 'mid',
          first_seen TEXT NOT NULL,
          scraped_at TEXT NOT NULL,
          title_tsv tsvector GENERATED ALWAYS AS
            (to_tsvector('simple', coalesce(title, ''))) STORED
        )
        """
    )
    op.execute("CREATE INDEX jobs_posted_idx ON jobs (posted_at DESC)")
    op.execute("CREATE INDEX jobs_workplace_idx ON jobs (workplace)")
    op.execute("CREATE INDEX jobs_type_idx ON jobs (type)")
    op.execute("CREATE INDEX jobs_experience_idx ON jobs (experience)")
    op.execute(
        "CREATE INDEX jobs_experience_posted_idx ON jobs (experience, posted_at DESC)"
    )
    op.execute("CREATE INDEX jobs_title_tsv_idx ON jobs USING GIN (title_tsv)")
    op.execute(
        "CREATE INDEX jobs_location_trgm_idx ON jobs USING GIN (location gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX jobs_company_trgm_idx ON jobs USING GIN (company gin_trgm_ops)"
    )
    op.execute(
        """
        CREATE TABLE jobs_staging (
          id TEXT PRIMARY KEY,
          url TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL,
          company TEXT NOT NULL,
          location TEXT NOT NULL,
          workplace TEXT NOT NULL,
          type TEXT NOT NULL,
          posted_at TEXT NOT NULL,
          tags TEXT NOT NULL,
          provider TEXT NOT NULL,
          experience TEXT NOT NULL DEFAULT 'mid',
          first_seen TEXT NOT NULL,
          scraped_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE dead_slugs (
          provider TEXT NOT NULL,
          slug TEXT NOT NULL,
          status INTEGER,
          seen_at TEXT NOT NULL,
          PRIMARY KEY (provider, slug)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sweep_meta (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          status TEXT NOT NULL,
          started_at TEXT,
          finished_at TEXT,
          duration_s DOUBLE PRECISION,
          job_count INTEGER,
          error_sample TEXT,
          next_run_at TEXT,
          counts_json TEXT
        )
        """
    )
    op.execute(
        """
        INSERT INTO sweep_meta
          (id, status, started_at, finished_at, duration_s, job_count,
           error_sample, next_run_at, counts_json)
        VALUES (1, 'idle', NULL, NULL, NULL, 0, '[]', NULL, '{}')
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sweep_meta")
    op.execute("DROP TABLE IF EXISTS dead_slugs")
    op.execute("DROP TABLE IF EXISTS jobs_staging")
    op.execute("DROP TABLE IF EXISTS jobs")
    op.execute("DROP TABLE IF EXISTS resumes")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS users")
