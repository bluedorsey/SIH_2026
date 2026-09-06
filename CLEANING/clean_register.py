"""
Register-style near-miss / UA-UC logs (CSV or Excel) -> normalised rows

Input : DATA/RAW/Register-style logs/*.csv | *.xlsx
Output: DATA/Processed/register/<file-stem>_clean.jsonl (+ .csv)
        DATA/Processed/register/register_stats.json

This is the same column-mapper the upload UI will need: registers from
different plants use different headers ("Near miss description
(Observation)", "Unsafe Act/Condition", "Details" ...) so headers are
matched by fragment against config.REGISTER_COLUMN_MAP.

Cleaning steps
- header -> canonical column mapping (unknown columns kept under `extra`)
- description: unicode/whitespace normalisation only (typos are kept on purpose:
  "desiganted", "traning", "gurd" are what real registers look like and the
  model must be robust to them; GLiNER spans must match the original text)
- category -> UA / UC / NM / INC
- sub_category upper-cased and whitespace-collapsed
- area/location normalised for grouping ("9 pb", "9PB", "9 PB" -> "9 PB") while the
  raw spelling is kept in `area_raw`
- date: "04-Mar" (no year) parsed with --register-year, else kept raw + flagged
- observer names replaced by a stable pseudonym hash (PII); raw names are NOT written
  unless --keep-names is passed
- exact + near duplicate descriptions flagged
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .common.dedup import mark_duplicates
from .common.io import write_csv, write_json, write_jsonl
from .common.text import clean_text, sha1, word_count
from .config import (
    MIN_TEXT_CHARS,
    OUT_REGISTER_DIR,
    RAW_REGISTER_DIR,
    REGISTER_CATEGORY_MAP,
    REGISTER_COLUMN_MAP,
)

log = logging.getLogger("clean.register")

_DATE_FORMATS_FULL = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d-%b-%y", "%d/%m/%y", "%m/%d/%Y")
_DATE_FORMATS_NOYEAR = ("%d-%b", "%d %b", "%d/%m", "%b-%d", "%d-%B")


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", str(h).strip().lower())


def map_columns(headers: list[str]) -> dict[str, str]:
    """raw header -> canonical column. First fragment match wins; 'area' is only used if no 'location' header exists."""
    mapping: dict[str, str] = {}
    taken: set[str] = set()
    for h in headers:
        nh = _norm_header(h)
        for canon, frags in REGISTER_COLUMN_MAP.items():
            if canon in taken:
                continue
            if any(f in nh for f in frags):
                # "sub-location" must not be swallowed by "location"/"area"
                if canon == "area" and ("sub" in nh):
                    continue
                if canon == "date" and "update" in nh:
                    continue
                mapping[h] = canon
                taken.add(canon)
                break
    return mapping


def _category(v: str | None) -> str | None:
    if not v:
        return None
    k = re.sub(r"[^a-z ]", "", str(v).lower()).strip()
    k = re.sub(r"\s+", " ", k)
    if k in REGISTER_CATEGORY_MAP:
        return REGISTER_CATEGORY_MAP[k]
    if "unsafe act" in k:
        return "UA"
    if "unsafe cond" in k:
        return "UC"
    if "near" in k and "miss" in k:
        return "NM"
    return v.strip().upper()


def _norm_area(v: str | None) -> str | None:
    """'9 pb' / '9PB' / '9 PB' -> '9 PB'; 'Sterio room' -> 'STERIO ROOM' (spelling untouched)."""
    if not v:
        return None
    s = clean_text(str(v)).upper()
    s = re.sub(r"(?<=\d)(?=[A-Z])", " ", s)      # 9PB -> 9 PB
    s = re.sub(r"(?<=[A-Z])(?=\d)", " ", s)      # PB9 -> PB 9
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def _parse_date(v: str | None, assume_year: int | None) -> tuple[str | None, bool]:
    """Returns (iso_date, year_was_assumed)."""
    if not v:
        return None, False
    s = clean_text(str(v)).replace(".", "-")
    for fmt in _DATE_FORMATS_FULL:
        try:
            return datetime.strptime(s, fmt).date().isoformat(), False
        except ValueError:
            continue
    if assume_year:
        for fmt in _DATE_FORMATS_NOYEAR:
            try:
                d = datetime.strptime(s, fmt).replace(year=assume_year)
                return d.date().isoformat(), True
            except ValueError:
                continue
    return None, False


def load_register(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, encoding="utf-8", encoding_errors="replace")


def clean_register(path: Path, *, assume_year: int | None = None, keep_names: bool = False) -> tuple[list[dict], dict]:
    df = load_register(path)
    df = df.dropna(how="all")
    mapping = map_columns([str(c) for c in df.columns])
    unmapped_cols = [c for c in df.columns if c not in mapping]
    if "description" not in mapping.values():
        raise SystemExit(f"{path.name}: could not find a description column in {list(df.columns)}")
    log.info("%s: %d rows; column mapping: %s; unmapped: %s", path.name, len(df), mapping, unmapped_cols)

    stem = re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_")
    rows: list[dict] = []
    for i, rec in enumerate(df.to_dict("records"), start=1):
        g = {mapping[k]: (None if (isinstance(v, float) and pd.isna(v)) else v) for k, v in rec.items() if k in mapping}
        extra = {k: v for k, v in rec.items() if k not in mapping and not (isinstance(v, float) and pd.isna(v))}
        desc = clean_text(g.get("description") or "")
        date_iso, assumed = _parse_date(g.get("date"), assume_year)
        observer = clean_text(g.get("observer") or "") or None
        row = {
            "id": f"reg_{stem}_{i:04d}",
            "source": "register",
            "source_file": path.name,
            "record_type": "near_miss",
            "sno": clean_text(str(g.get("sno") or "")) or None,
            "date_raw": g.get("date"),
            "date": date_iso,
            "date_year_assumed": assumed,
            "shift": clean_text(g.get("shift") or "") or None,
            "time_of_day": (clean_text(g.get("time_of_day") or "").title() or None),
            "category_raw": g.get("category"),
            "category": _category(g.get("category")),
            "sub_category": (clean_text(g.get("sub_category") or "").upper() or None),
            "area_raw": g.get("area"),
            "area": _norm_area(g.get("area")),
            "department": clean_text(g.get("department") or "") or None,
            "unit": clean_text(g.get("unit") or "") or None,
            "sub_location": clean_text(g.get("sub_location") or "") or None,
            "observer_id": sha1(observer.lower(), 8) if observer else None,
            "status": (clean_text(g.get("status") or "").upper() or None),
            "corrective_action": clean_text(g.get("corrective_action") or "") or None,
            "comments": clean_text(g.get("comments") or "") or None,
            "extra": {str(k): clean_text(str(v)) for k, v in extra.items()} or None,
            "description": desc,
            "description_words": word_count(desc),
            "text": desc,
        }
        if keep_names:
            row["observer"] = observer
        rows.append(row)

    n_raw = len(rows)
    rows = [r for r in rows if r["text"] and len(r["text"]) >= MIN_TEXT_CHARS]
    dup_stats = mark_duplicates(rows, text_field="text", id_field="id")
    stats = {
        "file": path.name,
        "column_mapping": mapping,
        "unmapped_columns": unmapped_cols,
        "raw_rows": n_raw,
        "dropped_empty_or_short": n_raw - len(rows),
        "rows": len(rows),
        "duplicates": dup_stats,
        "category_counts": _count(rows, "category"),
        "sub_category_counts": _count(rows, "sub_category"),
        "area_counts": _count(rows, "area"),
        "date_unparsed": sum(1 for r in rows if r["date"] is None),
        "date_year_assumed": sum(1 for r in rows if r["date_year_assumed"]),
        "words_min_median_max": _wstats(rows),
    }
    return rows, stats


def _wstats(rows: list[dict]) -> list[int]:
    ws = sorted(r["description_words"] for r in rows)
    return [ws[0], ws[len(ws) // 2], ws[-1]] if ws else [0, 0, 0]


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


def run(raw_dir: Path = RAW_REGISTER_DIR, out_dir: Path = OUT_REGISTER_DIR,
        assume_year: int | None = None, keep_names: bool = False) -> dict:
    all_rows: list[dict] = []
    all_stats: list[dict] = []
    files = sorted(p for p in raw_dir.iterdir() if p.suffix.lower() in (".csv", ".xlsx", ".xlsm", ".xls"))
    for f in files:
        rows, stats = clean_register(f, assume_year=assume_year, keep_names=keep_names)
        stem = re.sub(r"[^a-z0-9]+", "_", f.stem.lower()).strip("_")
        write_jsonl(rows, out_dir / f"{stem}_clean.jsonl")
        write_csv(rows, out_dir / f"{stem}_clean.csv")
        all_rows.extend(rows)
        all_stats.append(stats)
        log.info("%s -> %d rows (%d dups)", f.name, len(rows), stats["duplicates"]["exact_duplicates"] + stats["duplicates"]["near_duplicates"])
    write_json(all_stats, out_dir / "register_stats.json")
    return {"rows": all_rows, "stats": all_stats}


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
