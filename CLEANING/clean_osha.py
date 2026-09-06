"""
OSHA Severe Injury Reports CSV -> cleaned oil & gas contrast set

Input : DATA/RAW/OSHA Severe Injury Reports/January2015toNovember2025.csv  (~106k rows)
Output: DATA/Processed/osha/osha_oilgas.jsonl   (rows whose NAICS is oil & gas, ~2.9k)
        DATA/Processed/osha/osha_oilgas.csv
        DATA/Processed/osha/osha_all_clean.csv   (only with --osha-all: every row, cleaned)
        DATA/Processed/osha/osha_stats.json

Cleaning steps
- keep only the columns the project needs (config.OSHA_COLUMNS)
- NAICS to string (raw file mixes "213112" and 213112.0), oil & gas flag by prefix
- EventDate -> ISO date
- narrative: unicode/whitespace normalisation only (text is NOT rewritten)
- Hospitalized / Amputation / Loss of Eye -> int (they arrive as 1.0 / 0.0 / NaN)
- exact + near duplicate narratives flagged (same event filed twice)
- rows with an empty / too-short narrative dropped
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from .common.dedup import mark_duplicates
from .common.io import write_csv, write_json, write_jsonl
from .common.text import clean_text, sha1, word_count
from .config import MIN_TEXT_CHARS, OSHA_COLUMNS, OSHA_OILGAS_NAICS_PREFIXES, OUT_OSHA_DIR, RAW_OSHA_CSV

log = logging.getLogger("clean.osha")

_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%y")


def _parse_date(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().split(" ")[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _flag(v) -> int | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _naics(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s or None


def _naics_sector(naics: str | None) -> str | None:
    if not naics:
        return None
    if naics.startswith("211"):
        return "oil_gas_extraction"
    if naics.startswith("213111"):
        return "drilling_oil_gas_wells"
    if naics.startswith("213112"):
        return "support_activities_oil_gas"
    if naics.startswith("324110"):
        return "petroleum_refineries"
    return None


def load_raw(csv_path: Path = RAW_OSHA_CSV) -> pd.DataFrame:
    return pd.read_csv(csv_path, dtype=str, keep_default_na=True, encoding="utf-8", encoding_errors="replace",
                       low_memory=False)


def clean_frame(df: pd.DataFrame) -> list[dict]:
    missing = [c for c in OSHA_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"OSHA CSV is missing expected columns: {missing}")
    rows: list[dict] = []
    for rec in df[list(OSHA_COLUMNS)].to_dict("records"):
        r = {OSHA_COLUMNS[k]: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in rec.items()}
        narrative = clean_text(r.get("narrative") or "")
        naics = _naics(r.get("naics"))
        row = {
            "id": f"osha_{r.get('osha_id')}",
            "source": "osha_sir",
            "record_type": "severe_injury",
            "osha_id": r.get("osha_id"),
            "upa": r.get("upa"),
            "event_date": _parse_date(r.get("event_date_raw")),
            "event_year": None,
            "employer": clean_text(r.get("employer") or "") or None,
            "city": clean_text(r.get("city") or "").title() or None,
            "state": clean_text(r.get("state") or "").title() or None,
            "naics": naics,
            "naics_sector": _naics_sector(naics),
            "is_oilgas": bool(naics and naics.startswith(OSHA_OILGAS_NAICS_PREFIXES)),
            "hospitalized": _flag(r.get("hospitalized")),
            "amputation": _flag(r.get("amputation")),
            "loss_of_eye": _flag(r.get("loss_of_eye")),
            "nature": clean_text(r.get("nature") or "") or None,
            "part_of_body": clean_text(r.get("part_of_body") or "") or None,
            "event_type": clean_text(r.get("event_type") or "") or None,
            "source_of_injury": clean_text(r.get("source") or "") or None,
            "secondary_source": clean_text(r.get("secondary_source") or "") or None,
            "narrative": narrative,
            "narrative_words": word_count(narrative),
            "text": narrative,
        }
        row["event_year"] = int(row["event_date"][:4]) if row["event_date"] else None
        # OSHA SIR rows are actual injuries by definition -> useful contrast labels
        row["actual_injury"] = True
        row["actual_severity_hint"] = (
            "amputation" if row["amputation"] else
            "loss_of_eye" if row["loss_of_eye"] else
            "hospitalized" if row["hospitalized"] else "reported_severe"
        )
        rows.append(row)
    return rows


def run(csv_path: Path = RAW_OSHA_CSV, out_dir: Path = OUT_OSHA_DIR, keep_all: bool = False) -> dict:
    log.info("reading %s", csv_path.name)
    df = load_raw(csv_path)
    log.info("raw rows: %d, columns: %d", len(df), len(df.columns))
    rows = clean_frame(df)

    n_raw = len(rows)
    rows = [r for r in rows if r["narrative"] and len(r["narrative"]) >= MIN_TEXT_CHARS]
    n_short = n_raw - len(rows)

    oilgas = [r for r in rows if r["is_oilgas"]]
    dup_stats_og = mark_duplicates(oilgas, text_field="text", id_field="id")
    log.info("oil & gas subset: %d rows (%d exact dups, %d near dups)",
             len(oilgas), dup_stats_og["exact_duplicates"], dup_stats_og["near_duplicates"])

    stats = {
        "raw_rows": n_raw,
        "dropped_empty_or_short_narrative": n_short,
        "rows_after_filter": len(rows),
        "oilgas_rows": len(oilgas),
        "oilgas_by_sector": _count(oilgas, "naics_sector"),
        "oilgas_by_year": _count(oilgas, "event_year"),
        "oilgas_severity": _count(oilgas, "actual_severity_hint"),
        "oilgas_duplicates": dup_stats_og,
        "oilgas_unique_for_training": sum(1 for r in oilgas if not r["is_duplicate"]),
        "date_unparsed": sum(1 for r in rows if r["event_date"] is None),
        "naics_missing": sum(1 for r in rows if r["naics"] is None),
    }

    write_jsonl(oilgas, out_dir / "osha_oilgas.jsonl")
    write_csv(oilgas, out_dir / "osha_oilgas.csv")
    if keep_all:
        dup_stats_all = mark_duplicates(rows, text_field="text", id_field="id")
        stats["all_duplicates"] = dup_stats_all
        write_csv(rows, out_dir / "osha_all_clean.csv")
        log.info("wrote all %d cleaned rows (--osha-all)", len(rows))
    write_json(stats, out_dir / "osha_stats.json")
    return {"oilgas": oilgas, "stats": stats}


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
