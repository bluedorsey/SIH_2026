"""
IHM Stefanini industrial safety database (Kaggle, CC0) -> evaluation set

Input : DATA/RAW/Kaggle_IHM/IHMStefanini_industrial_safety_and_health_database_with_accidents_description.csv
Output: DATA/Processed/ihm/ihm_eval.jsonl (+csv, stats.json)

425 accident descriptions (Brazilian mining/metals, translated English) with an
ACTUAL level (I-V) and a POTENTIAL level (I-VI).  The only public dataset with
an explicit potential-severity label -> used ONLY to report agreement with the
model's verdict (potential IV-VI should land P_SIF / EXPOSURE / CAPACITY,
I-II should land LOW_ENERGY).  Never train on it.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .common.dedup import mark_duplicates
from .common.io import write_csv, write_json, write_jsonl
from .common.text import clean_text, word_count
from .config import OUT_IHM_DIR, RAW_IHM_DIR

log = logging.getLogger("clean.ihm")
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}


def run(raw_dir: Path = RAW_IHM_DIR, out_dir: Path = OUT_IHM_DIR) -> dict:
    src = next(raw_dir.glob("*.csv"))
    df = pd.read_csv(src, dtype=str)
    df = df.rename(columns={c: c.strip() for c in df.columns})
    rows: list[dict] = []
    for i, r in enumerate(df.to_dict("records"), start=1):
        desc = clean_text(str(r.get("Description") or ""))
        if not desc:
            continue
        actual = _ROMAN.get(str(r.get("Accident Level", "")).strip().upper())
        potential = _ROMAN.get(str(r.get("Potential Accident Level", "")).strip().upper())
        rows.append({
            "id": f"ihm_{i:03d}",
            "source": "kaggle_ihm",
            "record_type": "accident",
            "date": (str(r.get("Data") or "")[:10] or None),
            "country": r.get("Countries"), "site": r.get("Local"), "industry_sector": r.get("Industry Sector"),
            "actual_level": actual, "potential_level": potential,
            "potential_minus_actual": (potential - actual) if actual and potential else None,
            "expected_verdict_group": ("SIF_POTENTIAL" if potential and potential >= 4 else "LOW_ENERGY" if potential and potential <= 2 else "BORDERLINE"),
            "employee_or_third_party": r.get("Employee or Third Party"),
            "critical_risk": clean_text(str(r.get("Critical Risk") or "")) or None,
            "text": desc, "words": word_count(desc), "actual_injury": True,
            "split_hint": "eval_only",
        })
    dup = mark_duplicates(rows, text_field="text", id_field="id")
    stats = {"rows": len(rows), "duplicates": dup,
             "actual_level": _count(rows, "actual_level"), "potential_level": _count(rows, "potential_level"),
             "expected_verdict_group": _count(rows, "expected_verdict_group"), "critical_risk_top": dict(list(_count(rows, "critical_risk").items())[:15])}
    write_jsonl(rows, out_dir / "ihm_eval.jsonl")
    write_csv(rows, out_dir / "ihm_eval.csv")
    write_json(stats, out_dir / "stats.json")
    log.info("ihm: %d rows (eval only)", len(rows))
    return {"rows": rows, "stats": stats}


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
