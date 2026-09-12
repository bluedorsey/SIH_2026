"""
Distillation CLI.

    python -m TRAINING.distill.run_distill --job generate --limit 2 --dry-run     # see the prompts, no API call
    python -m TRAINING.distill.run_distill --job generate --limit 2               # pilot: 2 batches (~40 rows)
    python -m TRAINING.distill.run_distill --job rewind --limit 30                # pilot: 30 seeds
    python -m TRAINING.distill.run_distill --job label  --limit 60
    python -m TRAINING.distill.run_distill --job all                              # rewind + generate + label, resumable
    python -m TRAINING.distill.run_distill --job agree --limit 500                # second-teacher agreement sample
    python -m TRAINING.distill.run_distill --job rewind --backend sarvam          # pin one provider
    python -m TRAINING.distill.run_distill --status                               # progress + spend

Keys come from .env (GEMINI_API, GROQ_API_1/2, SARVAM_API_1/2, OPENROUTER_API_1/2).  Failover between lanes
and providers is automatic; re-running the same command resumes where it stopped.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.distill"  # noqa: A001

from ..config import DISTILLED_RAW_DIR, available_lanes  # noqa: E402
from .runner import run_job  # noqa: E402


def status() -> None:
    print(f"lanes with keys: {[l['lane'] for l in available_lanes()] or 'NONE - fill .env'}")
    for job in ("generate", "rewind", "label", "agree"):
        sp = DISTILLED_RAW_DIR / f"{job}.state.json"
        if sp.exists():
            st = json.loads(sp.read_text(encoding="utf-8"))
            s = st["stats"]
            print(f"{job:9} batches {s['batches']:5}  rows {s['rows']:6}  rejects {s['rejects']:5}  "
                  f"failed {len(st['failed']):3}  tokens in/out {s['tokens_in']}/{s['tokens_out']}  lanes {s.get('by_lane')}")
        else:
            print(f"{job:9} not started")
    up = DISTILLED_RAW_DIR / "usage.json"
    if up.exists():
        print("usage:", json.dumps(json.loads(up.read_text(encoding='utf-8')), indent=1)[:1500])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the teacher on prompts §1 / §2 / §3 with checkpoints and failover")
    ap.add_argument("--job", choices=["generate", "rewind", "label", "agree", "all"], default=None)
    ap.add_argument("--backend", choices=["sarvam", "gemini", "openrouter", "groq", "nvidia", "mistral", "cerebras"], default=None, help="pin one provider")
    ap.add_argument("--limit", type=int, default=None, help="generate: batches; rewind: seeds; label: rows")
    ap.add_argument("--total-rows", type=int, default=None, help="generate: total rows to produce (default 4500)")
    ap.add_argument("--source", default=None, help="rewind/label: only seeds whose source contains this (e.g. iogp, alert_iadc, osha)")
    ap.add_argument("--dry-run", action="store_true", help="build prompts, call nothing")
    ap.add_argument("--reverse", action="store_true", help="work the batch list from the end (second window on the same job)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    try:  # per-process log file so a window's history survives closing it (DATA/distilled/raw/logs/<job>_<pid>.log)
        from ..config import DISTILLED_RAW_DIR  # noqa: WPS433
        import os  # noqa: WPS433

        logdir = DISTILLED_RAW_DIR / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(logdir / f"{a.job or 'status'}_{os.getpid()}.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(fh)
    except Exception:  # noqa: BLE001
        pass
    if a.status or not a.job:
        status()
        return 0
    jobs = ["rewind", "generate", "label"] if a.job == "all" else [a.job]
    for job in jobs:
        run_job(job, backend=a.backend, limit=a.limit, dry_run=a.dry_run, source_filter=a.source, total_rows=a.total_rows, reverse=a.reverse)
    status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
