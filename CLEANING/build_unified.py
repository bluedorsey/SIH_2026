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



def _from_osha_abstract(r: dict) -> dict:
    return {
        "id": r["id"], "source": "osha_abstracts", "record_type": r["record_type"], "text": r["text"],
        "context": {"title": r["title"], "keywords": r["keywords"]},
        "labels": {"life_saving_rules": [], "lsr_source": None, "actual_injury": True,
                   "actual_fatality": r["actual_fatality"], "verdict_prior": "H_SIF" if r["actual_fatality"] else "H_SIF_or_L_SIF",
                   "event_tag_11class": r.get("event_tag_11class"), "fatal_cause": r.get("fatal_cause")},
        "meta": {"event_year": r["event_year"], "is_oilgas": r["is_oilgas"], "oilgas_score": r["oilgas_score"], "sic": r.get("sic"),
                 "construction_activity": r.get("construction_activity"), "diagnosis": r.get("diagnosis"), "fall_distance_ft": r.get("fall_distance_ft")},
        "teacher_prompt": "rewind" if r["is_oilgas"] else None,
        # non-oil&gas abstracts are an evaluation pool only (US, all industries, post-injury) - never sent to the teacher
        "split_hint": "seed_never_test" if r["is_oilgas"] else "eval_pool",
    }


def _from_msha(r: dict) -> dict:
    no_inj = r["record_type"] == "no_injury_event"
    return {
        "id": r["id"], "source": "msha", "record_type": r["record_type"], "text": r["text"], "context": {},
        "labels": {"life_saving_rules": [], "lsr_source": None, "actual_injury": not no_inj, "actual_fatality": r["actual_fatality"],
                   "verdict_prior": "P_SIF_or_CAPACITY" if no_inj else "H_SIF"},
        "meta": {"date": r["date"], "year": r["year"], "classification": r["classification"], "accident_type": r["accident_type"],
                 "activity": r["activity"], "injury_source": r["injury_source"], "is_oilgas": r["is_oilgas"], "coal_metal": r["coal_metal"]},
        "teacher_prompt": "label",
        "split_hint": "seed_never_test" if r["split_hint"] == "train_candidate" else "eval_pool",
    }


def _from_alert(r: dict) -> dict:
    return {
        "id": r["id"], "source": r["source"], "record_type": r["record_type"], "text": r["text"],
        "context": {"title": r["title"], "what_went_wrong": r["what_went_wrong"], "corrective_actions": r["corrective_actions"],
                    "potential_consequence": r.get("potential_consequence"), "text_hi": r.get("text_hi")},
        "labels": {"life_saving_rules": r["life_saving_rules"], "lsr_source": f"{r['alert_source'].lower()}_tag" if r["life_saving_rules"] else None,
                   "actual_injury": r["actual_injury"], "actual_fatality": r["actual_fatality"], "actual_outcome": r.get("actual_outcome"),
                   "verdict_prior": ("H_SIF" if r["actual_fatality"] else
                                     "L_SIF" if r.get("actual_outcome") in ("lost_time_injury", "restricted_work") else
                                     "P_SIF_or_CAPACITY")},
        "meta": {"alert_source": r["alert_source"], "domain": r["domain"], "off_domain_marine": r["off_domain_marine"], "date": r["date"],
                 "year": r.get("year"), "url": r["url"], "reference": r.get("reference"), "onshore_offshore": r["onshore_offshore"], "tags": r["tags"]},
        "teacher_prompt": "rewind",
        "split_hint": "off_domain" if r["off_domain_marine"] else "seed_never_test",
    }


def _from_gold(r: dict) -> dict:
    return {
        "id": r["id"], "source": "gold_180", "record_type": "observation", "text": r["text"],
        "context": {"rationale": r["rationale"]},
        "labels": {"life_saving_rules": r["life_saving_rules"], "lsr_source": "gold", "actual_injury": None, "actual_fatality": False,
                   "verdict_prior": None, "sif_potential": r["sif_potential"], "statement_type": r["statement_type"],
                   "energy_types": r["energy_types"], "barrier": r["barrier"], "barrier_status": r["barrier_status"],
                   "verdict_candidates": r["verdict_candidates"], "trap_family": r["trap_family"]},
        "meta": {"language": r["language"], "script": r["script"], "fold": r["fold"], "review_flags": r["review_flags"]},
        "teacher_prompt": None,
        "split_hint": "gold_test",
    }


def _from_ihm(r: dict) -> dict:
    return {
        "id": r["id"], "source": "kaggle_ihm", "record_type": "accident", "text": r["text"], "context": {},
        "labels": {"life_saving_rules": [], "lsr_source": None, "actual_injury": True, "actual_fatality": None,
                   "verdict_prior": None, "potential_level": r["potential_level"], "actual_level": r["actual_level"],
                   "expected_verdict_group": r["expected_verdict_group"]},
        "meta": {"industry_sector": r["industry_sector"], "critical_risk": r["critical_risk"], "country": r["country"]},
        "teacher_prompt": None,
        "split_hint": "eval_only",
    }


_DUP_PRIORITY = {"fatal": 5, "permanent_impairment": 4, "severe_injury": 3, "hipo": 2, "near_miss": 1}
CONTRAST_TEACHER_CAP = 1000   # post-injury OSHA SIR rows sent to the teacher (§3 Label); the rest = evaluation pool


def _dup_priority(r: dict) -> int:
    if r.get("split_hint") in ("gold_test", "eval_only"):
        return 9
    return _DUP_PRIORITY.get(r.get("record_type"), 0)


def build(iogp: list[dict], osha: list[dict], register: list[dict], out_dir: Path = OUT_UNIFIED_DIR,
          osha_abstracts: list[dict] | None = None, msha: list[dict] | None = None, alerts: list[dict] | None = None,
          gold: list[dict] | None = None, ihm: list[dict] | None = None) -> dict:
    rows: list[dict] = []
    rows += [_from_iogp(r) for r in iogp if r.get("text")]
    rows += [_from_osha(r) for r in osha if r.get("text")]
    rows += [_from_register(r) for r in register if r.get("text")]
    rows += [_from_osha_abstract(r) for r in (osha_abstracts or []) if r.get("text") and not r.get("is_duplicate")]
    rows += [_from_msha(r) for r in (msha or []) if r.get("text") and r.get("split_hint") == "train_candidate"]
    rows += [_from_alert(r) for r in (alerts or []) if r.get("text")]
    rows += [_from_gold(r) for r in (gold or []) if r.get("text")]
    rows += [_from_ihm(r) for r in (ihm or []) if r.get("text")]

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

    # contrast rows (post-injury OSHA SIR) are capped for the teacher: the plan trains on <= 1,000 of them, the rest is evaluation
    contrast = [r for r in rows if not r["is_duplicate"] and r["split_hint"] == "contrast_test_candidate"]
    contrast.sort(key=lambda r: -(r["meta"].get("event_year") or 0))
    contrast_ids = {r["id"] for r in contrast[:CONTRAST_TEACHER_CAP]}
    for r in contrast[CONTRAST_TEACHER_CAP:]:
        r["split_hint"] = "eval_pool"
    teacher = [{
        "input_id": r["id"], "source": r["source"], "record_type": r["record_type"],
        "teacher_prompt": r["teacher_prompt"], "text": r["text"],
        "context": r["context"] if r["source"] == "iogp" or r["source"].startswith("alert_") else None,
        "life_saving_rules": r["labels"]["life_saving_rules"], "meta": r["meta"],
    } for r in rows if not r["is_duplicate"] and r["teacher_prompt"] and (r["split_hint"] == "seed_never_test" or r["id"] in contrast_ids)]
    write_jsonl(teacher, out_dir / "teacher_input.jsonl")

    # any training-side row that near-duplicates a gold/eval row must be dropped from teacher input (leakage)
    eval_ids = {r["id"] for r in rows if r["split_hint"] in ("gold_test", "eval_only")}
    leaks = [r["id"] for r in rows if r["is_duplicate"] and r["duplicate_of"] in eval_ids and r["id"] not in eval_ids] + \
            [r["duplicate_of"] for r in rows if r["id"] in eval_ids and r["is_duplicate"] and r["duplicate_of"] not in eval_ids]
    if leaks:
        log.warning("%d training rows near-duplicate a gold/eval row and were removed from teacher_input: %s", len(leaks), leaks[:10])
        teacher = [t for t in teacher if t["input_id"] not in set(leaks)]
        write_jsonl(teacher, out_dir / "teacher_input.jsonl")

    return {
        "rows": rows,
        "stats": {
            "total": len(rows), "unique": n_unique, "duplicates": dup_stats,
            "by_source": _count(rows, "source"), "by_record_type": _count(rows, "record_type"),
            "by_teacher_prompt": _count(rows, "teacher_prompt"), "by_split_hint": _count(rows, "split_hint"),
            "teacher_input_rows": len(teacher),
        },
    }


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
