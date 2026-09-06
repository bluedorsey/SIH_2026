"""
Merge every cleaned source into one corpus with a single schema.

Output: DATA/Processed/unified/corpus.jsonl
        DATA/Processed/unified/corpus.csv           (flat view: id, source, record_type, text, lsr, split_hint)
        DATA/Processed/unified/teacher_input.jsonl  (only the columns the teacher prompts need, dups removed)

One line per record:
{
  "id": "...",
  "source": "iogp" | "osha_sir" | "register",
  "record_type": "fatal" | "hipo" | "permanent_impairment" | "severe_injury" | "near_miss",
  "text": "<the free text the model / teacher reads>",
  "context": {...other free-text fields (what_went_wrong, corrective_actions ...)},
  "labels": {
      "life_saving_rules": [...],          # gold from IOGP, [] elsewhere
      "lsr_source": "iogp_gold" | null,
      "actual_injury": true/false/null,    # IOGP fatal/PI + OSHA = true, hipo = per narrative (null), register = false
      "actual_fatality": true/false/null,
      "verdict_prior": "H_SIF" | "P_SIF_or_CAPACITY" | "H_SIF_or_L_SIF" | null   # what the teacher prompts say to expect
  },
  "meta": {...categorical fields (date, country, region, function, cause, activity, area ...)},
  "teacher_prompt": "rewind" | "label",       # prompts.md §2 vs §3
  "split_hint": "seed_never_test" | "contrast_test_candidate" | "seed_examples",
  "is_duplicate": bool, "duplicate_of": id|null
}
"""
from __future__ import annotations

import logging
from pathlib import Path

from .common.dedup import mark_duplicates
from .common.io import write_csv, write_jsonl
from .config import OUT_UNIFIED_DIR

log = logging.getLogger("clean.unified")


def _from_iogp(r: dict) -> dict:
    fatal = r["record_type"] == "fatal"
    pi = r["record_type"] == "permanent_impairment"
    return {
        "id": r["id"],
        "source": "iogp",
        "record_type": r["record_type"],
        "text": r["text"],
        "context": {
            "narrative": r["narrative"],
            "what_went_wrong": r["what_went_wrong"],
            "corrective_actions": r["corrective_actions"],
            "causal_factors": r["causal_factors"],
        },
        "labels": {
            "life_saving_rules": r["life_saving_rules"],
            "lsr_source": "iogp_gold" if r["life_saving_rules"] else None,
            "actual_injury": True if (fatal or pi) else None,
            "actual_fatality": True if fatal else False,
            "verdict_prior": "H_SIF" if (fatal or pi) else "P_SIF_or_CAPACITY",
        },
        "meta": {
            "date": r["date"], "report_year": r["report_year"], "country": r["country"], "region": r["region"],
            "onshore_offshore": r["onshore_offshore"], "function": r["function"], "cause": r["cause"],
            "activity": r["activity"], "number_of_deaths": r["number_of_deaths"],
            "number_of_pi_injuries": r["number_of_pi_injuries"], "victim_employer": r["victim_employer"],
            "victim_occupation": r["victim_occupation"], "victim_body_part": r["victim_body_part"],
            "victim_nature_of_injury": r["victim_nature_of_injury"], "source_file": r["source_file"],
            "page_start": r["page_start"],
        },
        "teacher_prompt": "rewind",
        "split_hint": "seed_never_test",
    }


def _from_osha(r: dict) -> dict:
    return {
        "id": r["id"],
        "source": "osha_sir",
        "record_type": "severe_injury",
        "text": r["text"],
        "context": {},
        "labels": {
            "life_saving_rules": [],
            "lsr_source": None,
            "actual_injury": True,
            "actual_fatality": None,
            "verdict_prior": "H_SIF_or_L_SIF",
        },
        "meta": {
            "date": r["event_date"], "event_year": r["event_year"], "state": r["state"], "naics": r["naics"],
            "naics_sector": r["naics_sector"], "hospitalized": r["hospitalized"], "amputation": r["amputation"],
            "loss_of_eye": r["loss_of_eye"], "nature": r["nature"], "part_of_body": r["part_of_body"],
            "event_type": r["event_type"], "source_of_injury": r["source_of_injury"],
        },
        "teacher_prompt": "label",
        "split_hint": "contrast_test_candidate",
    }


def _from_register(r: dict) -> dict:
    return {
        "id": r["id"],
        "source": "register",
        "record_type": "near_miss",
        "text": r["text"],
        "context": {"corrective_action": r["corrective_action"], "comments": r["comments"]},
        "labels": {
            "life_saving_rules": [],
            "lsr_source": None,
            "actual_injury": False,
            "actual_fatality": False,
            "verdict_prior": None,
        },
        "meta": {
            "date": r["date"], "date_raw": r["date_raw"], "time_of_day": r["time_of_day"], "category": r["category"],
            "sub_category": r["sub_category"], "area": r["area"], "status": r["status"], "source_file": r["source_file"],
        },
        "teacher_prompt": "label",
        "split_hint": "seed_examples",
    }


_DUP_PRIORITY = {"fatal": 5, "permanent_impairment": 4, "severe_injury": 3, "hipo": 2, "near_miss": 1}


def _dup_priority(r: dict) -> int:
    return _DUP_PRIORITY.get(r.get("record_type"), 0)


def build(iogp: list[dict], osha: list[dict], register: list[dict], out_dir: Path = OUT_UNIFIED_DIR) -> dict:
    rows: list[dict] = []
    rows += [_from_iogp(r) for r in iogp if r.get("text")]
    rows += [_from_osha(r) for r in osha if r.get("text")]
    rows += [_from_register(r) for r in register if r.get("text")]

    # cross-source duplicate check.  IOGP prints the same incident in the HiPo report AND in the
    # permanent-impairment / fatal report; keep the version with the most informative outcome.
    dup_stats = mark_duplicates(rows, text_field="text", id_field="id", priority=_dup_priority)
    n_unique = sum(1 for r in rows if not r["is_duplicate"])
    log.info("unified corpus: %d rows, %d unique (%d exact, %d near dups)",
             len(rows), n_unique, dup_stats["exact_duplicates"], dup_stats["near_duplicates"])

    write_jsonl(rows, out_dir / "corpus.jsonl")
    flat = [{
        "id": r["id"], "source": r["source"], "record_type": r["record_type"],
        "life_saving_rules": "|".join(r["labels"]["life_saving_rules"]),
        "verdict_prior": r["labels"]["verdict_prior"], "teacher_prompt": r["teacher_prompt"],
        "split_hint": r["split_hint"], "is_duplicate": r["is_duplicate"], "words": len(r["text"].split()),
        "text": r["text"],
    } for r in rows]
    write_csv(flat, out_dir / "corpus.csv")

    teacher = [{
        "input_id": r["id"], "source": r["source"], "record_type": r["record_type"],
        "teacher_prompt": r["teacher_prompt"], "text": r["text"],
        "context": r["context"] if r["source"] == "iogp" else None,
        "life_saving_rules": r["labels"]["life_saving_rules"], "meta": r["meta"],
    } for r in rows if not r["is_duplicate"]]
    write_jsonl(teacher, out_dir / "teacher_input.jsonl")

    return {
        "rows": rows,
        "stats": {
            "total": len(rows), "unique": n_unique, "duplicates": dup_stats,
            "by_source": _count(rows, "source"), "by_record_type": _count(rows, "record_type"),
            "by_teacher_prompt": _count(rows, "teacher_prompt"),
        },
    }


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
