"""email verify, google sub, nullable password

Revision ID: 002_auth_providers
Revises: 001_initial
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_auth_providers"
down_revision: Union[str, Sequence[str], None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT NULL")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS users_google_sub_key
          ON users (google_sub)
          WHERE google_sub IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE users
           SET email_verified_at = created_at
         WHERE email_verified_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS users_google_sub_key")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_sub")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_verified_at")
    op.execute(
        "ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL"
    )
