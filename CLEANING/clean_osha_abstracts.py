"""
OSHA fatality / catastrophe investigation summaries (IMIS "accident abstracts") -> cleaned rows

Input : DATA/RAW/OSHA Accident Abstracts/osha_abstracts_16k.xlsx       (16,323 rows, 2004-2013, keyword-tagged)
        DATA/RAW/OSHA Accident Abstracts/osha_construction_4470_metadata.xlsx  (optional: cause / fatcause / diagnosis)
        DATA/RAW/OSHA Accident Abstracts/osha_construction_tagged1000.xlsx     (optional: 11-class event tag)
Output: DATA/Processed/osha_abstracts/abstracts.jsonl (+csv, stats.json)

What it does
- reads the header-less 16k sheet (id | title | summary | keywords | -)
- normalises whitespace (the source has double spaces everywhere), keeps wording
- keyword string -> list; event year from the text; fatality / hospitalisation flags from the text
- oil & gas domain flag by STRONG/WEAK term lists (config.OILGAS_*), with a score
- joins the construction labels (cause, fatcause, diagnosis, fall distance, 11-class tag) on id when available
- exact + near duplicates flagged (360 exact duplicates in the raw file)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from .common.dedup import mark_duplicates
from .common.io import write_csv, write_json, write_jsonl
from .common.text import clean_text, word_count
from .config import MIN_TEXT_CHARS, OILGAS_STRONG_TERMS, OILGAS_WEAK_TERMS, OUT_OSHA_ABSTRACTS_DIR, RAW_OSHA_ABSTRACTS_DIR

log = logging.getLogger("clean.osha_abstracts")

_STRONG = re.compile(r"\b(?:" + "|".join(OILGAS_STRONG_TERMS) + r")\b", re.I)
_WEAK = re.compile(r"\b(?:" + "|".join(OILGAS_WEAK_TERMS) + r")\b", re.I)
_FATAL = re.compile(r"\b(was killed|were killed|died|death|fatal(?:ly|ity)?|pronounced dead|succumbed|deceased)\b", re.I)
_HOSP = re.compile(r"\b(hospitali[sz]ed|hospital)\b", re.I)
_AMP = re.compile(r"\bamputat", re.I)
_YEAR = re.compile(r"\b((?:19|20)\d\d)\b")


def oilgas_score(text: str) -> tuple[int, list[str]]:
    strong = sorted({m.group(0).lower() for m in _STRONG.finditer(text)})
    weak = sorted({m.group(0).lower() for m in _WEAK.finditer(text)})
    return 2 * len(strong) + len(weak), strong + weak


def load_16k(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, header=None)
    df = df.iloc[:, :4]
    df.columns = ["osha_id", "title", "summary", "keywords"]
    return df


def load_construction(dir_: Path) -> pd.DataFrame | None:
    meta = dir_ / "osha_construction_4470_metadata.xlsx"
    tagged = dir_ / "osha_construction_tagged1000.xlsx"
    if not meta.exists():
        return None
    m = pd.read_excel(meta, sheet_name=0)
    m = m.rename(columns={"SUMMARY": "summary_c", "fall dist": "fall_distance_ft", "1st occupation": "occupation_primary"})
    keep = [c for c in ["id", "industry", "diagnosis", "occupation_primary", "fall_distance_ft", "cause", "fatcause"] if c in m.columns]
    m = m[keep].rename(columns={"id": "osha_id", "industry": "sic", "cause": "construction_activity", "fatcause": "fatal_cause"})
    if tagged.exists():
        t = pd.read_excel(tagged)
        if "Tagged2" in t.columns:
            m = m.merge(t[["id", "Tagged2"]].rename(columns={"id": "osha_id", "Tagged2": "event_tag_11class"}), on="osha_id", how="left")
    return m


def _clean_cat(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().strip(",").strip()
    if s in ("[]", "", "nan"):
        return None
    return s


def run(raw_dir: Path = RAW_OSHA_ABSTRACTS_DIR, out_dir: Path = OUT_OSHA_ABSTRACTS_DIR) -> dict:
    src = raw_dir / "osha_abstracts_16k.xlsx"
    df = load_16k(src)
    log.info("raw rows: %d", len(df))
    cons = load_construction(raw_dir)
    if cons is not None:
        df = df.merge(cons, on="osha_id", how="left")
        log.info("construction labels joined for %d rows", df["construction_activity"].notna().sum() if "construction_activity" in df else 0)

    rows: list[dict] = []
    for r in df.to_dict("records"):
        summary = clean_text(str(r.get("summary") or ""))
        title = clean_text(str(r.get("title") or ""))
        if len(summary) < MIN_TEXT_CHARS:
            continue
        kws = [k.strip().lower() for k in re.split(r"\s{2,}|,|;", str(r.get("keywords") or "")) if k.strip() and k.strip().lower() != "nan"]
        blob = f"{title} {summary} {' '.join(kws)}"
        score, terms = oilgas_score(blob)
        yr = _YEAR.search(summary)
        row = {
            "id": f"osha_abs_{r['osha_id']}",
            "source": "osha_abstracts",
            "record_type": "fatal" if _FATAL.search(summary) else "severe_injury",
            "osha_id": str(r["osha_id"]),
            "title": title or None,
            "event_year": int(yr.group(1)) if yr and 1990 <= int(yr.group(1)) <= 2026 else None,
            "keywords": kws,
            "is_oilgas": bool(any(t for t in terms if _STRONG.fullmatch(t))),
            "oilgas_score": score,
            "oilgas_terms": terms,
            "actual_fatality": bool(_FATAL.search(summary)),
            "hospitalized": bool(_HOSP.search(summary)),
            "amputation": bool(_AMP.search(summary)),
            "sic": _clean_cat(r.get("sic")),
            "construction_activity": _clean_cat(r.get("construction_activity")),
            "fatal_cause": _clean_cat(r.get("fatal_cause")),
            "diagnosis": _clean_cat(r.get("diagnosis")),
            "occupation": _clean_cat(r.get("occupation_primary")),
            "fall_distance_ft": (int(r["fall_distance_ft"]) if "fall_distance_ft" in r and pd.notna(r.get("fall_distance_ft")) and int(r["fall_distance_ft"]) >= 0 else None),
            "event_tag_11class": _clean_cat(r.get("event_tag_11class")),
            "narrative": summary,
            "narrative_words": word_count(summary),
            "text": summary,
            "actual_injury": True,
        }
        rows.append(row)

    dup = mark_duplicates(rows, text_field="text", id_field="id")
    n_og = sum(1 for r in rows if r["is_oilgas"])
    stats = {
        "raw_rows": int(len(df)), "rows": len(rows), "duplicates": dup,
        "oilgas_rows": n_og, "oilgas_unique": sum(1 for r in rows if r["is_oilgas"] and not r["is_duplicate"]),
        "fatal_rows": sum(1 for r in rows if r["actual_fatality"]),
        "with_construction_labels": sum(1 for r in rows if r["construction_activity"] or r["fatal_cause"]),
        "with_11class_tag": sum(1 for r in rows if r["event_tag_11class"]),
        "by_year": _count(rows, "event_year"),
        "top_oilgas_terms": _top_terms(rows),
    }
    write_jsonl(rows, out_dir / "abstracts.jsonl")
    write_csv(rows, out_dir / "abstracts.csv")
    write_json(stats, out_dir / "stats.json")
    log.info("osha abstracts: %d rows, %d oil&gas, %d fatal, %d dups", len(rows), n_og, stats["fatal_rows"], dup["exact_duplicates"] + dup["near_duplicates"])
    return {"rows": rows, "stats": stats}


def _top_terms(rows: list[dict], n: int = 25) -> dict:
    c: dict = {}
    for r in rows:
        if r["is_oilgas"]:
            for t in r["oilgas_terms"]:
                c[t] = c.get(t, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1])[:n])


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
