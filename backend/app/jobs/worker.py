"""Run the ATS sweep loop without serving HTTP."""

from __future__ import annotations

import logging
import time

from . import scheduler, store

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info("jobs worker starting")
    store.init()
    scheduler.start()
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        log.info("jobs worker stopping")
        scheduler.stop()


if __name__ == "__main__":
    main()
