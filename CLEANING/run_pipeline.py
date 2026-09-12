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

from . import (  # noqa: E402
    build_unified, clean_alerts, clean_gold, clean_ihm, clean_iogp, clean_msha, clean_osha, clean_osha_abstracts,
    clean_register, clean_terms, evaluate_readiness, report,
)
from .config import (  # noqa: E402
    PROCESSED_DIR, RAW_ALERTS_DIR, RAW_GOLD_DIR, RAW_IHM_DIR, RAW_IOGP_DIR, RAW_MSHA_DIR, RAW_OSHA_ABSTRACTS_DIR,
    RAW_OSHA_CSV, RAW_REGISTER_DIR, RAW_TERMS_JSON,
)

log = logging.getLogger("clean")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Clean the raw SIH_26 datasets into DATA/Processed/")
    ap.add_argument("--iogp", action="store_true", help="parse the IOGP fatal / HiPo / PI PDFs")
    ap.add_argument("--osha", action="store_true", help="clean the OSHA severe-injury CSV")
    ap.add_argument("--register", action="store_true", help="clean register-style near-miss logs")
    ap.add_argument("--terms", action="store_true", help="clean the terms.json glossary")
    ap.add_argument("--gold", action="store_true", help="clean the Golden_180 Hinglish gold set")
    ap.add_argument("--osha-abstracts", action="store_true", help="clean the 16k OSHA accident abstracts (GitHub mirror)")
    ap.add_argument("--ihm", action="store_true", help="clean the Kaggle IHM eval set")
    ap.add_argument("--msha", action="store_true", help="clean MSHA Accidents.txt (after fetch_msha)")
    ap.add_argument("--alerts", action="store_true", help="parse IADC/IMCA/StepChange/OISD alerts (after fetch_alerts)")
    ap.add_argument("--unified-only", action="store_true", help="re-run nothing; rebuild unified corpus + readiness from DATA/Processed")
    ap.add_argument("--no-readiness", action="store_true", help="skip the training-readiness report")
    ap.add_argument("--no-unified", action="store_true", help="skip building the unified corpus")
    ap.add_argument("--osha-all", action="store_true", help="also write every OSHA row (not just oil & gas) to osha_all_clean.csv")
    ap.add_argument("--register-year", type=int, default=None, help="year to assume for register dates like '04-Mar'")
    ap.add_argument("--keep-names", action="store_true", help="keep observer names in register output (default: pseudonymised)")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)
    if args.unified_only:
        return args
    if not (args.iogp or args.osha or args.register or args.terms or args.gold or args.osha_abstracts or args.ihm or args.msha or args.alerts):
        args.iogp = args.osha = args.register = args.terms = args.gold = args.osha_abstracts = args.ihm = args.msha = args.alerts = True
    return args


def _load_missing_from_disk(results: dict) -> None:
    """Fill `results` with previously processed outputs for stages that were not (re)run now."""
    from .common.io import read_jsonl  # noqa: WPS433
    from .config import (  # noqa: WPS433
        OUT_ALERTS_DIR, OUT_GOLD_DIR, OUT_IHM_DIR, OUT_IOGP_DIR, OUT_MSHA_DIR, OUT_OSHA_ABSTRACTS_DIR, OUT_OSHA_DIR, OUT_REGISTER_DIR,
    )
    spec = {
        "iogp": ("records", OUT_IOGP_DIR / "records.jsonl"),
        "osha": ("oilgas", OUT_OSHA_DIR / "osha_oilgas.jsonl"),
        "osha_abstracts": ("rows", OUT_OSHA_ABSTRACTS_DIR / "abstracts.jsonl"),
        "msha": ("rows", OUT_MSHA_DIR / "msha_selected.jsonl"),
        "alerts": ("rows", OUT_ALERTS_DIR / "alerts.jsonl"),
        "gold": ("rows", OUT_GOLD_DIR / "gold.jsonl"),
        "ihm": ("rows", OUT_IHM_DIR / "ihm_eval.jsonl"),
    }
    for key, (field, path) in spec.items():
        if key not in results and path.is_file():
            results[key] = {field: read_jsonl(path), "stats": {}, "loaded_from_disk": True}
            log.info("%s: loaded %d rows from %s", key, len(results[key][field]), path.name)
    if "register" not in results and OUT_REGISTER_DIR.is_dir():
        rows = [r for p in sorted(OUT_REGISTER_DIR.glob("*_clean.jsonl")) for r in read_jsonl(p)]
        if rows:
            results["register"] = {"rows": rows, "stats": [], "loaded_from_disk": True}
            log.info("register: loaded %d rows from disk", len(rows))


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

    def _optional(flag: bool, name: str, exists: bool, fn, where):
        if not flag:
            return
        if exists:
            try:
                results[name] = fn()
            except Exception as exc:  # noqa: BLE001
                log.error("%s failed: %s", name, exc)
        else:
            log.warning("%s: nothing found at %s (run the fetcher on a machine with internet)", name, where)

    _optional(args.gold, "gold", RAW_GOLD_DIR.is_dir() and any(RAW_GOLD_DIR.glob("*.csv")), clean_gold.run, RAW_GOLD_DIR)
    _optional(args.osha_abstracts, "osha_abstracts", (RAW_OSHA_ABSTRACTS_DIR / "osha_abstracts_16k.xlsx").is_file(), clean_osha_abstracts.run, RAW_OSHA_ABSTRACTS_DIR)
    _optional(args.ihm, "ihm", RAW_IHM_DIR.is_dir() and any(RAW_IHM_DIR.glob("*.csv")), clean_ihm.run, RAW_IHM_DIR)
    _optional(args.msha, "msha", (RAW_MSHA_DIR / "Accidents.txt").is_file(), clean_msha.run, RAW_MSHA_DIR)
    _optional(args.alerts, "alerts", RAW_ALERTS_DIR.is_dir() and any(RAW_ALERTS_DIR.rglob("*")), clean_alerts.run, RAW_ALERTS_DIR)

    # stages not run in this invocation are loaded from DATA/Processed so the unified corpus is always complete
    _load_missing_from_disk(results)

    if not args.no_unified and any(k in results for k in ("iogp", "osha", "register", "osha_abstracts", "msha", "alerts", "gold")):
        results["unified"] = build_unified.build(
            results.get("iogp", {}).get("records", []),
            results.get("osha", {}).get("oilgas", []),
            results.get("register", {}).get("rows", []),
            osha_abstracts=results.get("osha_abstracts", {}).get("rows", []),
            msha=results.get("msha", {}).get("rows", []),
            alerts=results.get("alerts", {}).get("rows", []),
            gold=results.get("gold", {}).get("rows", []),
            ihm=results.get("ihm", {}).get("rows", []),
        )
    if not args.no_readiness:
        try:
            results["readiness"] = evaluate_readiness.evaluate(results)
        except Exception as exc:  # noqa: BLE001
            log.error("readiness report failed: %s", exc)

    elapsed = time.time() - t0
    report.write_report(results, elapsed)
    report.write_manifest(results, vars(args), elapsed)
    log.info("done in %.1fs -> %s", elapsed, PROCESSED_DIR)
    print(f"\nWrote {PROCESSED_DIR}\nSee {PROCESSED_DIR / 'quality_report.md'} and {PROCESSED_DIR / 'training_readiness.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
