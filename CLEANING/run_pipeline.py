"""
SIH_26 data-cleaning pipeline - entry point.

    python -m CLEANING.run_pipeline            # everything (run from the repo root, E:\\SIH_26)
    python -m CLEANING.run_pipeline --iogp     # only the IOGP PDFs
    python -m CLEANING.run_pipeline --osha --osha-all
    python -m CLEANING.run_pipeline --register --register-year 2024
    python -m CLEANING.run_pipeline --terms

Raw data is never modified.  Everything lands in DATA/Processed/.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# allow `python CLEANING/run_pipeline.py` as well as `python -m CLEANING.run_pipeline`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "CLEANING"  # noqa: A001

from . import build_unified, clean_iogp, clean_osha, clean_register, clean_terms, report  # noqa: E402
from .config import PROCESSED_DIR, RAW_IOGP_DIR, RAW_OSHA_CSV, RAW_REGISTER_DIR, RAW_TERMS_JSON  # noqa: E402

log = logging.getLogger("clean")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Clean the raw SIH_26 datasets into DATA/Processed/")
    ap.add_argument("--iogp", action="store_true", help="parse the IOGP fatal / HiPo / PI PDFs")
    ap.add_argument("--osha", action="store_true", help="clean the OSHA severe-injury CSV")
    ap.add_argument("--register", action="store_true", help="clean register-style near-miss logs")
    ap.add_argument("--terms", action="store_true", help="clean the terms.json glossary")
    ap.add_argument("--no-unified", action="store_true", help="skip building the unified corpus")
    ap.add_argument("--osha-all", action="store_true", help="also write every OSHA row (not just oil & gas) to osha_all_clean.csv")
    ap.add_argument("--register-year", type=int, default=None, help="year to assume for register dates like '04-Mar'")
    ap.add_argument("--keep-names", action="store_true", help="keep observer names in register output (default: pseudonymised)")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)
    if not (args.iogp or args.osha or args.register or args.terms):
        args.iogp = args.osha = args.register = args.terms = True
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(levelname)-7s %(name)s: %(message)s")
    t0 = time.time()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    if args.iogp:
        if RAW_IOGP_DIR.is_dir():
            results["iogp"] = clean_iogp.run()
        else:
            log.warning("IOGP folder not found: %s", RAW_IOGP_DIR)
    if args.osha:
        if RAW_OSHA_CSV.is_file():
            results["osha"] = clean_osha.run(keep_all=args.osha_all)
        else:
            log.warning("OSHA CSV not found: %s", RAW_OSHA_CSV)
    if args.register:
        if RAW_REGISTER_DIR.is_dir():
            results["register"] = clean_register.run(assume_year=args.register_year, keep_names=args.keep_names)
        else:
            log.warning("register folder not found: %s", RAW_REGISTER_DIR)
    if args.terms:
        if RAW_TERMS_JSON.is_file():
            results["terms"] = clean_terms.run()
        else:
            log.warning("terms.json not found: %s", RAW_TERMS_JSON)

    if not args.no_unified and any(k in results for k in ("iogp", "osha", "register")):
        results["unified"] = build_unified.build(
            results.get("iogp", {}).get("records", []),
            results.get("osha", {}).get("oilgas", []),
            results.get("register", {}).get("rows", []),
        )

    elapsed = time.time() - t0
    report.write_report(results, elapsed)
    report.write_manifest(results, vars(args), elapsed)
    log.info("done in %.1fs -> %s", elapsed, PROCESSED_DIR)
    print(f"\nWrote {PROCESSED_DIR}\nSee {PROCESSED_DIR / 'quality_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
