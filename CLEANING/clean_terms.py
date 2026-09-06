"""
terms.json (domain glossary) -> validated, de-duplicated glossary + lookup table

Input : DATA/RAW/terms/terms.json
Output: DATA/Processed/terms/glossary_clean.json      (list of entries, one per canonical term)
        DATA/Processed/terms/glossary_clean.csv
        DATA/Processed/terms/variant_lookup.json      {variant (lower-cased): canonical term}
        DATA/Processed/terms/terms_stats.json

Problems in the raw file that this fixes
- the top level is 58 objects + ONE nested list of 97 objects -> flattened
- duplicate terms (PSV, NRV, BOP, SCBA, ELCB, JCB ...) -> merged, variants unioned,
  conflicting fields recorded in `merge_conflicts`
- `lsr` is sometimes JSON null and sometimes the string "null"; spelling drifts
  ("Work Authorisation" / "Work Authorization") -> canonical IOGP names or null
- `safety_signal` uses "statement_type" / "outcome" / "none" -> mapped to the
  GLiNER role names from prompts.md ("statement_cue", "outcome_cue", null)
- variants de-duplicated case-insensitively, variant == term removed
- every entry validated against the expected schema; problems listed in stats
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from .common.io import write_csv, write_json
from .common.lsr import canonical_lsr
from .common.text import clean_text
from .config import OUT_TERMS_DIR, RAW_TERMS_JSON, TERMS_SIGNAL_MAP

log = logging.getLogger("clean.terms")

EXPECTED_KEYS = {"term", "variants", "meaning", "category", "safety_signal", "example_line", "lsr", "confidence", "source_hint"}
VALID_CATEGORIES = {"equipment", "abbreviation", "barrier", "activity", "location", "hazard", "phrase", "other"}
VALID_CONFIDENCE = {"high", "medium", "low"}


def _flatten(obj) -> list[dict]:
    out: list[dict] = []
    if isinstance(obj, dict):
        # either a single entry or {"terms": [...]}
        if "term" in obj:
            out.append(obj)
        else:
            for v in obj.values():
                out.extend(_flatten(v))
    elif isinstance(obj, list):
        for x in obj:
            out.extend(_flatten(x))
    return out


def _norm_signal(v) -> tuple[str | None, bool]:
    """-> (role, was_known)"""
    k = clean_text(str(v or "")).lower()
    if k in TERMS_SIGNAL_MAP:
        return TERMS_SIGNAL_MAP[k], True
    return None, False


def clean_entries(raw: list[dict]) -> tuple[list[dict], dict]:
    merged: dict[str, dict] = {}
    problems: list[dict] = []
    n_dupes = 0
    unknown_signals: dict[str, int] = {}

    for i, e in enumerate(raw):
        term = clean_text(str(e.get("term") or ""))
        if not term:
            problems.append({"index": i, "problem": "empty term"})
            continue
        key = term.lower()
        extra_keys = set(e) - EXPECTED_KEYS
        missing_keys = EXPECTED_KEYS - set(e)
        if extra_keys or missing_keys:
            problems.append({"index": i, "term": term, "extra_keys": sorted(extra_keys), "missing_keys": sorted(missing_keys)})

        variants = e.get("variants") or []
        if isinstance(variants, str):
            variants = [variants]
        variants = [clean_text(str(v)) for v in variants if clean_text(str(v))]

        signal, known = _norm_signal(e.get("safety_signal"))
        if not known:
            unknown_signals[str(e.get("safety_signal"))] = unknown_signals.get(str(e.get("safety_signal")), 0) + 1

        lsr_raw = e.get("lsr")
        lsr = canonical_lsr(None if lsr_raw in (None, "null", "None", "") else str(lsr_raw))
        if lsr_raw not in (None, "null", "None", "") and lsr is None:
            problems.append({"index": i, "term": term, "problem": f"unmapped lsr {lsr_raw!r}"})

        category = clean_text(str(e.get("category") or "")).lower() or None
        if category and category not in VALID_CATEGORIES:
            problems.append({"index": i, "term": term, "problem": f"unexpected category {category!r}"})
        confidence = clean_text(str(e.get("confidence") or "")).lower() or None
        if confidence and confidence not in VALID_CONFIDENCE:
            problems.append({"index": i, "term": term, "problem": f"unexpected confidence {confidence!r}"})

        entry = {
            "term": term,
            "variants": variants,
            "meaning": clean_text(str(e.get("meaning") or "")) or None,
            "category": category,
            "safety_signal": signal,
            "safety_signal_raw": e.get("safety_signal"),
            "example_line": clean_text(str(e.get("example_line") or "")) or None,
            "lsr": lsr,
            "lsr_raw": lsr_raw if lsr_raw not in ("null",) else None,
            "confidence": confidence,
            "source_hint": clean_text(str(e.get("source_hint") or "")) or None,
            "merged_from": 1,
            "merge_conflicts": [],
        }

        if key in merged:
            n_dupes += 1
            m = merged[key]
            m["merged_from"] += 1
            for v in variants:
                if v.lower() not in {x.lower() for x in m["variants"]}:
                    m["variants"].append(v)
            for fld in ("meaning", "category", "safety_signal", "lsr", "confidence", "example_line"):
                if entry[fld] and m[fld] and entry[fld] != m[fld]:
                    m["merge_conflicts"].append({"field": fld, "kept": m[fld], "dropped": entry[fld]})
                elif entry[fld] and not m[fld]:
                    m[fld] = entry[fld]
            # keep the first example_line, but preserve additional ones
            if entry["example_line"] and entry["example_line"] != m["example_line"]:
                m.setdefault("extra_example_lines", []).append(entry["example_line"])
        else:
            merged[key] = entry

    # final tidy: de-dupe variants, drop variant == term
    for m in merged.values():
        seen: set[str] = set()
        vs: list[str] = []
        for v in m["variants"]:
            k = v.lower()
            if k == m["term"].lower() or k in seen:
                continue
            seen.add(k)
            vs.append(v)
        m["variants"] = vs
        if not m["merge_conflicts"]:
            m["merge_conflicts"] = None

    entries = sorted(merged.values(), key=lambda x: (x["category"] or "", x["term"].lower()))
    stats = {
        "raw_entries": len(raw),
        "unique_terms": len(entries),
        "duplicate_terms_merged": n_dupes,
        "entries_with_conflicts": sum(1 for e in entries if e["merge_conflicts"]),
        "by_category": _count(entries, "category"),
        "by_safety_signal": _count(entries, "safety_signal"),
        "by_lsr": _count(entries, "lsr"),
        "unknown_safety_signal_values": unknown_signals,
        "schema_problems": problems,
        "total_variants": sum(len(e["variants"]) for e in entries),
    }
    return entries, stats


def build_lookup(entries: list[dict]) -> tuple[dict[str, str], list[dict]]:
    """variant -> canonical term.  Collisions (same variant under two terms) are reported."""
    lookup: dict[str, str] = {}
    collisions: list[dict] = []
    for e in entries:
        for v in [e["term"], *e["variants"]]:
            k = v.lower()
            if k in lookup and lookup[k] != e["term"]:
                collisions.append({"variant": v, "terms": [lookup[k], e["term"]]})
                continue
            lookup[k] = e["term"]
    return lookup, collisions


def run(src: Path = RAW_TERMS_JSON, out_dir: Path = OUT_TERMS_DIR) -> dict:
    with open(src, "r", encoding="utf-8") as fh:
        raw_obj = json.load(fh)
    raw = _flatten(raw_obj)
    entries, stats = clean_entries(raw)
    lookup, collisions = build_lookup(entries)
    stats["variant_collisions"] = collisions
    write_json(entries, out_dir / "glossary_clean.json")
    write_csv(entries, out_dir / "glossary_clean.csv")
    write_json(lookup, out_dir / "variant_lookup.json")
    write_json(stats, out_dir / "terms_stats.json")
    log.info("terms: %d raw -> %d unique (%d merged, %d variants, %d collisions)",
             stats["raw_entries"], stats["unique_terms"], stats["duplicate_terms_merged"], stats["total_variants"], len(collisions))
    return {"entries": entries, "lookup": lookup, "stats": stats}


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
