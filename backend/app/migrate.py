"""Run Alembic upgrades from app startup."""

from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

log = logging.getLogger(__name__)


def upgrade_head() -> None:
    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(cfg, "head")
    log.info("alembic upgrade head complete")
