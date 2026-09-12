"""
MSHA Accident Injuries data set -> English near-miss-like rows + a small fatal/PD contrast set

Input : DATA/RAW/MSHA/Accidents.txt   (pipe-delimited; from Accidents.zip via CLEANING/fetch/fetch_msha.py)
Output: DATA/Processed/msha/msha_selected.jsonl (+csv, stats.json)

Why: DEGREE_INJURY code 00 = "Accident only" - a reportable event with NO injury.
Those rows are the closest public English analogue to a near-miss / unsafe-event
report (energy released, nobody hurt -> P_SIF / CAPACITY territory).  Codes 01
(fatality) and 02 (permanent disability) give a small H_SIF contrast set.

Filters (config.MSHA_*)
- keep DEGREE_INJURY in {00, 01, 02}
- drop underground-mining-only classifications (fall of roof/rib/face, gas/dust ignition, inundation ...)
- drop rows with UG_LOCATION set to an underground working (no oil & gas analogue) when the column exists
- cap: 1,000 no-injury rows + 300 fatal/PD rows selected for training; everything else kept with split_hint = "eval_pool"
- narrative normalised (upper-case narratives are sentence-cased), oil & gas terms scored, duplicates flagged
"""
from __future__ import annotations

import logging
import random
import re
from pathlib import Path

import pandas as pd

from .clean_osha_abstracts import oilgas_score
from .common.dedup import mark_duplicates
from .common.io import write_csv, write_json, write_jsonl
from .common.text import clean_text, word_count
from .config import (
    MIN_TEXT_CHARS,
    MSHA_DEGREE_KEEP,
    MSHA_DROP_CLASSIFICATION_RE,
    MSHA_KEEP_COLUMNS,
    MSHA_TRAIN_CAP_FATAL_PD,
    MSHA_TRAIN_CAP_NO_INJURY,
    OUT_MSHA_DIR,
    RAW_MSHA_DIR,
)

log = logging.getLogger("clean.msha")
_DROP_CLASS = re.compile(MSHA_DROP_CLASSIFICATION_RE, re.I)
_UG_RE = re.compile(r"underground|face|entry|crosscut|longwall|shaft|slope", re.I)


def _sentence_case(s: str) -> str:
    """MSHA narratives are often ALL CAPS - lower them but keep acronyms of <= 4 letters."""
    if not s or sum(ch.isupper() for ch in s) < 0.6 * max(1, sum(ch.isalpha() for ch in s)):
        return s
    out = s.lower()
    out = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    for acr in ("loto", "ppe", "msha", "cpr", "ems", "ug", "h2s", "co", "psi", "hp", "kv"):
        out = re.sub(rf"\b{acr}\b", acr.upper(), out, flags=re.I)
    return out


def load(path: Path) -> pd.DataFrame:
    """Stream the 270 MB pipe-delimited file in chunks, keeping only the needed columns and the degree codes we use
    (00 no-injury, 01 fatal, 02 permanent disability) - peak memory stays well under 1 GB."""
    wanted = set(MSHA_KEEP_COLUMNS)
    header = pd.read_csv(path, sep="|", nrows=0, encoding="utf-8", encoding_errors="replace")
    cols = [c for c in header.columns if c.strip().upper() in wanted]
    missing = [c for c in ("NARRATIVE", "DEGREE_INJURY_CD") if c not in {x.strip().upper() for x in cols}]
    if missing:
        raise SystemExit(f"Accidents.txt missing columns {missing}; got {[c.strip().upper() for c in header.columns][:30]}")
    parts = []
    for chunk in pd.read_csv(path, sep="|", dtype=str, usecols=cols, encoding="utf-8", encoding_errors="replace",
                             on_bad_lines="skip", chunksize=100_000):
        chunk.columns = [c.strip().upper() for c in chunk.columns]
        deg = chunk["DEGREE_INJURY_CD"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        parts.append(chunk[deg.isin(MSHA_DEGREE_KEEP)])
    df = pd.concat(parts, ignore_index=True) if parts else header
    df.attrs["n_raw_rows"] = sum(1 for _ in open(path, "rb")) - 1
    return df


def run(raw_dir: Path = RAW_MSHA_DIR, out_dir: Path = OUT_MSHA_DIR, seed: int = 13) -> dict:
    src = raw_dir / "Accidents.txt"
    df = load(src)
    n_raw = df.attrs.get("n_raw_rows", len(df))
    df["DEGREE_INJURY_CD"] = df["DEGREE_INJURY_CD"].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df = df[df["DEGREE_INJURY_CD"].isin(MSHA_DEGREE_KEEP)]
    n_degree = len(df)
    if "CLASSIFICATION" in df.columns:
        df = df[~df["CLASSIFICATION"].astype(str).str.contains(_DROP_CLASS)]
    if "UG_LOCATION" in df.columns:
        ug = df["UG_LOCATION"].astype(str).str.strip()
        df = df[~(ug.str.contains(_UG_RE) & ~ug.str.contains(r"no value|surface|n/a|nan", case=False))]
    n_filtered = len(df)
    keep = [c for c in MSHA_KEEP_COLUMNS if c in df.columns]
    df = df[keep]

    rows: list[dict] = []
    for i, r in enumerate(df.to_dict("records"), start=1):
        narr = clean_text(_sentence_case(str(r.get("NARRATIVE") or "")))
        if len(narr) < MIN_TEXT_CHARS:
            continue
        code = r["DEGREE_INJURY_CD"].zfill(2)
        score, terms = oilgas_score(narr)
        rows.append({
            "id": f"msha_{i:06d}",
            "source": "msha",
            "record_type": {"00": "no_injury_event", "01": "fatal", "02": "permanent_impairment"}[code],
            "degree_injury_cd": code, "degree_injury": r.get("DEGREE_INJURY"),
            "date": _date(r.get("ACCIDENT_DT")), "year": _int(r.get("CAL_YR")),
            "mine_id": r.get("MINE_ID"), "coal_metal": r.get("COAL_METAL_IND"), "subunit": r.get("SUBUNIT"),
            "classification": r.get("CLASSIFICATION"), "accident_type": r.get("ACCIDENT_TYPE"),
            "activity": r.get("ACTIVITY"), "injury_source": r.get("INJURY_SOURCE"), "nature_injury": r.get("NATURE_INJURY"),
            "body_part": r.get("INJ_BODY_PART"), "days_lost": _int(r.get("DAYS_LOST")), "no_injuries": _int(r.get("NO_INJURIES")),
            "mining_equipment": r.get("MINING_EQUIP"),
            "is_oilgas": score >= 2, "oilgas_score": score, "oilgas_terms": terms,
            "actual_injury": code != "00", "actual_fatality": code == "01",
            "narrative": narr, "narrative_words": word_count(narr), "text": narr,
        })
    dup = mark_duplicates(rows, text_field="text", id_field="id")

    # training selection: prefer oil&gas-scored + recent rows; the rest stays as eval pool
    rng = random.Random(seed)
    def pick(cands: list[dict], cap: int) -> set[str]:
        cands = [c for c in cands if not c["is_duplicate"] and c["narrative_words"] >= 12]
        cands.sort(key=lambda c: (-c["oilgas_score"], -(c["year"] or 0), rng.random()))
        return {c["id"] for c in cands[:cap]}
    train_ids = pick([r for r in rows if r["record_type"] == "no_injury_event"], MSHA_TRAIN_CAP_NO_INJURY)
    train_ids |= pick([r for r in rows if r["record_type"] != "no_injury_event"], MSHA_TRAIN_CAP_FATAL_PD)
    for r in rows:
        r["split_hint"] = "train_candidate" if r["id"] in train_ids else "eval_pool"

    stats = {
        "raw_rows": n_raw, "after_degree_filter": n_degree, "after_classification_filter": n_filtered, "rows": len(rows),
        "by_record_type": _count(rows, "record_type"), "duplicates": dup,
        "train_candidates": len(train_ids), "oilgas_rows": sum(1 for r in rows if r["is_oilgas"]),
        "by_year": _count(rows, "year"), "top_classification": dict(list(_count(rows, "classification").items())[:15]),
    }
    write_jsonl(rows, out_dir / "msha_selected.jsonl")
    write_csv([r for r in rows if r["split_hint"] == "train_candidate"], out_dir / "msha_train_candidates.csv")
    write_json(stats, out_dir / "stats.json")
    log.info("msha: %d raw -> %d kept (%s); %d train candidates", n_raw, len(rows), stats["by_record_type"], len(train_ids))
    return {"rows": rows, "stats": stats}


def _date(v) -> str | None:
    if not v or str(v).strip() in ("", "nan"):
        return None
    s = str(v).strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return pd.to_datetime(s, format=fmt).date().isoformat()
        except Exception:  # noqa: BLE001
            continue
    return None


def _int(v) -> int | None:
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return None


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
