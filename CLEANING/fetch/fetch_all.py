"""Run every fetcher. Needs internet (run on your laptop, not in the sandbox)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "CLEANING.fetch"  # noqa: A001

from . import fetch_alerts, fetch_github_mirrors, fetch_msha  # noqa: E402

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    for name, fn in [("github mirrors", fetch_github_mirrors.run), ("msha", fetch_msha.run),
                     ("alerts", lambda: fetch_alerts.main(["--source", "all"]))]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("fetch").error("%s failed: %s", name, exc)
