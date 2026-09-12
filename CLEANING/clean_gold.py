"""
Hinglish gold set (Golden_180) -> §0-schema labels + review flags

Input : DATA/RAW/Golden_180/*.csv   (id, report_text, language, statement_type, sif_potential, confidence,
                                     energy_source, lsr, barrier, barrier_status, exposure, trap_type, rationale)
Output: DATA/Processed/gold/gold.jsonl (+csv, stats.json, review_queue.csv)

The text is already clean and is kept byte-for-byte.  What changes is the labels:
- statement_type  -> prompts.md §0 vocabulary (observed | hypothetical | historical | training_example |
                     corrective_completed | condition_only) ; raw kept in statement_type_raw
- lsr             -> list of canonical IOGP names ("NONE" -> []) ; raw kept
- energy_source   -> energy_types list (gravity | motion | electrical | pressure | thermal | chemical | mechanical | radiation | biological)
- barrier (free text) -> barrier taxonomy name via keyword rules (energy_isolation, gas_test, entry_permit, fall_arrest,
                     tool_lanyard, drop_zone_barricade, exclusion_zone, lifting_plan, hot_work_permit, machine_guard, ptw, ppe) ; raw kept
- barrier_status  -> absent | present_effective | present_ineffective | pseudo | unknown
- sif_potential   -> kept (YES/NO/UNCERTAIN) + verdict_candidates derived from the EEI questions the labels imply
- trap_type       -> trap_family (negation, historical, hypothetical, corrective_completed, contradiction, low_energy_injury_word,
                     capacity, vague, sarcasm_minimising, duplicate_cluster, india_context, language, positive, unscorable, other)
- review_flags    -> inconsistencies for a human (energy none but YES, multi_rule with one rule, 1-3 word text, ...)
- split           -> "gold_test" for every row (never train); `fold` 0-4 stratified by sif_potential for few-shot experiments
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from .common.io import write_csv, write_json, write_jsonl
from .common.lsr import canonical_lsr_list
from .common.text import clean_text, sha1, word_count
from .config import OUT_GOLD_DIR, RAW_GOLD_DIR

log = logging.getLogger("clean.gold")

STATEMENT_MAP = {
    "observed": "observed", "hypothetical": "hypothetical", "historical": "historical",
    "training": "training_example", "training_example": "training_example",
    "corrective_closed": "corrective_completed", "corrective_completed": "corrective_completed",
    "condition_only": "condition_only",
    "positive": "observed",          # a positive observation is still an observed statement (verdict SUCCESS)
    "suggestion": "hypothetical",    # "should install X" is not an observed event
    "unscorable": "condition_only",  # "Nil" / "Same as above" -> nothing observed; verdict INSUFFICIENT/NON_EVENT
}
ENERGY_MAP = {
    "none": [], "gravity_height": ["gravity"], "suspended_load": ["gravity", "mechanical"], "excavation_collapse": ["gravity"],
    "vehicle": ["motion"], "mechanical_motion": ["mechanical", "motion"], "electrical": ["electrical"], "pressure": ["pressure"],
    "thermal_fire": ["thermal"], "toxic_atmosphere": ["chemical"], "oxygen_deficiency": ["chemical"], "chemical": ["chemical"],
    "radiation": ["radiation"], "biological": ["biological"], "drowning": ["water"],
}
BARRIER_RULES = [  # (regex on raw barrier text, taxonomy name)
    (r"loto|isolation|lock ?out|de-?energi", "energy_isolation"),
    (r"gas test|gas detect|lel|atmospher|o2|h2s|ventilat", "gas_test"),
    (r"entry permit|confined space permit|entry authori", "entry_permit"),
    (r"hot work permit|hot work", "hot_work_permit"),
    (r"permit to work|ptw|work permit|permit\b", "ptw"),
    (r"fall protection|fall arrest|harness|lanyard|lifeline|anchorage|edge protection|guard ?rail|handrail", "fall_arrest"),
    (r"tool lanyard|tool tether|drop(ped)? object|secondary retention", "tool_lanyard"),
    (r"barricad|drop zone|exclusion zone|cordon|restricted area|line of fire|standing clear", "exclusion_zone"),
    (r"lifting plan|lift plan|tag ?line|rigging|swl|load chart|crane", "lifting_plan"),
    (r"guard|guarding|interlock|machine", "machine_guard"),
    (r"shoring|benching|trench|excavation support|sloping", "exclusion_zone"),
    (r"containment|pressure relief|psv|relief valve|isolation valve|integrity|nrv|bop|well control", "energy_isolation"),
    (r"ppe|helmet|goggles|gloves|respirat|scba|life jacket|boots|hand protection|eye protection|head protection", "ppe"),
    (r"housekeeping|escape route|signage|training|competen|supervis|communication|reporting|inspection|maintenance|procedure|sop|jsa|tbt", "management_control"),
]
STATUS_MAP = {"failed": "absent", "degraded": "present_ineffective", "intact": "present_effective", "unknown": "unknown", "not_applicable": None}
TRAP_FAMILY_RULES = [
    (r"negation", "negation"), (r"historical", "historical"), (r"hypothetical|suggestion", "hypothetical"),
    (r"corrective|historical_closed", "corrective_completed"), (r"contradict|ppe_x|trivial_ppe|borderline_ppe|ppe_ground", "contradiction_ppe"),
    (r"injury_but_low|low_sif|numbers_matter|missing_unit|missing_number|borderline_height", "low_energy_or_numbers"),
    (r"capacity|barrier_worked|mitigation_barrier|detection_barrier|instrument_barrier|partial_barrier|negation_barrier_intact", "capacity_or_barrier_status"),
    (r"vague|unscorable|boilerplate|pattern_statement|quota_gaming", "vague_or_unscorable"),
    (r"sarcasm|minimising", "sarcasm_minimising"), (r"duplicate", "duplicate_cluster"),
    (r"^india_|monsoon|wildlife|lightning|remote|pilferage|public_access|rig_move|soft_soil|heat|disruption|power|road|improvised", "india_context"),
    (r"language|typo|spelling|hinglish", "language_noise"), (r"positive", "positive_observation"),
    (r"multi_rule|multiple", "multi_rule_or_event"), (r"process_safety|no_exposure|lone_working|simops|well_control|dropped_object|drowning|deliberate_bypass|blind_spot|communication|competency|life_altering|recurrence|near_miss|no_injury_but_sif", "domain_scenario"),
]


def map_barrier(raw: str | None) -> str | None:
    if not raw:
        return None
    s = str(raw).lower().strip()
    if s in ("none", "", "n/a", "null"):
        return None
    for rx, name in BARRIER_RULES:
        if re.search(rx, s):
            return name
    return "other"


def trap_family(raw: str | None) -> str:
    s = (raw or "").lower().strip()
    if s in ("", "none", "nan"):
        return "none"
    for rx, fam in TRAP_FAMILY_RULES:
        if re.search(rx, s):
            return fam
    return "other"


def verdict_candidates(sif: str, statement: str, energy: list[str], status: str | None, exposure: str | None, text: str) -> list[str]:
    """Which §0 verdicts are compatible with the coarse gold labels (for evaluation, NOT a training label)."""
    if statement in ("hypothetical", "historical", "training_example"):
        return ["NON_EVENT"]
    if sif == "UNCERTAIN":
        return ["INSUFFICIENT"] if not energy else ["INSUFFICIENT", "EXPOSURE"]
    if sif == "NO":
        if not energy:
            return ["LOW_ENERGY", "NON_EVENT"]
        if status == "present_effective":
            return ["SUCCESS", "CAPACITY"]
        return ["LOW_ENERGY", "SUCCESS", "NON_EVENT"]
    # YES
    released = bool(re.search(r"\b(gir|gira|fell|fall|slipped|released|leak|spill|hit|struck|toota|phat|burst|nikla|contact)\b", text.lower()))
    if status == "present_effective":
        return ["CAPACITY"] if released else ["SUCCESS", "EXPOSURE"]
    if released:
        return ["P_SIF", "EXPOSURE"]
    return ["EXPOSURE", "P_SIF"]


def run(raw_dir: Path = RAW_GOLD_DIR, out_dir: Path = OUT_GOLD_DIR) -> dict:
    src = next(raw_dir.glob("*.csv"))
    df = pd.read_csv(src, dtype=str).fillna("")
    rows: list[dict] = []
    for r in df.to_dict("records"):
        text = str(r["report_text"])
        text_norm = clean_text(text)
        flags: list[str] = []
        if text_norm != text:
            flags.append("text_changed_by_normaliser")
        st_raw = r["statement_type"].strip().lower()
        st = STATEMENT_MAP.get(st_raw)
        if st is None:
            st, _ = "observed", flags.append(f"unknown_statement_type:{st_raw}")
        lsr, unmapped = canonical_lsr_list(None if r["lsr"].strip().upper() == "NONE" else r["lsr"])
        if unmapped:
            flags.append("lsr_unmapped:" + "|".join(unmapped))
        energy = ENERGY_MAP.get(r["energy_source"].strip().lower())
        if energy is None:
            energy, _ = [], flags.append(f"unknown_energy:{r['energy_source']}")
        status = STATUS_MAP.get(r["barrier_status"].strip().lower(), "unknown")
        barrier = map_barrier(r["barrier"])
        if barrier == "ppe":
            status = "pseudo" if status in ("present_effective", "present_ineffective", "absent") else status
        sif = r["sif_potential"].strip().upper()
        words = word_count(text)
        trap = trap_family(r["trap_type"])
        # review flags
        if sif == "YES" and not energy:
            flags.append("sif_yes_but_energy_none")
        if "multi" in r["trap_type"].lower() and len(lsr) < 2:
            flags.append("multi_rule_but_single_lsr")
        if words <= 3:
            flags.append("very_short_text")
        if sif == "YES" and not lsr:
            flags.append("sif_yes_no_lsr")
        if st in ("hypothetical", "historical", "training_example") and sif == "YES":
            flags.append("non_event_statement_but_sif_yes")
        if r["exposure"].strip().lower() == "absent" and sif == "YES":
            flags.append("exposure_absent_but_sif_yes")
        try:
            conf = float(r["confidence"])
        except ValueError:
            conf, _ = None, flags.append("confidence_not_numeric")
        rows.append({
            "id": f"gold_{r['id']}", "gold_id": r["id"], "source": "gold_180", "record_type": "observation",
            "text": text, "words": words,
            "language": r["language"].strip().lower(),
            "script": "devanagari" if re.search(r"[ऀ-ॿ]", text) else ("bengali_assamese" if re.search(r"[ঀ-৿]", text) else "latin"),
            "sif_potential": sif, "confidence": conf,
            "statement_type": st, "statement_type_raw": st_raw,
            "life_saving_rules": lsr, "lsr_raw": r["lsr"],
            "energy_types": energy, "energy_source_raw": r["energy_source"],
            "barrier": barrier, "barrier_raw": r["barrier"], "barrier_status": status, "barrier_status_raw": r["barrier_status"],
            "exposure": (r["exposure"].strip().lower() or None),
            "trap_type_raw": r["trap_type"], "trap_family": trap,
            "verdict_candidates": verdict_candidates(sif, st, energy, status, r["exposure"].strip().lower(), text),
            "rationale": r["rationale"],
            "review_flags": flags,
            "split": "gold_test",
        })
    # 5 stratified folds by sif_potential for few-shot experiments (never used as the final test)
    for cls in sorted({x["sif_potential"] for x in rows}):
        members = [x for x in rows if x["sif_potential"] == cls]
        for k, x in enumerate(sorted(members, key=lambda y: sha1(y["text"]))):
            x["fold"] = k % 5
    stats = {
        "rows": len(rows), "sif_potential": _count(rows, "sif_potential"), "statement_type": _count(rows, "statement_type"),
        "lsr": _lsr(rows), "energy_types": _multi(rows, "energy_types"), "barrier": _count(rows, "barrier"),
        "barrier_status": _count(rows, "barrier_status"), "language": _count(rows, "language"), "script": _count(rows, "script"),
        "trap_family": _count(rows, "trap_family"), "rows_with_review_flags": sum(1 for x in rows if x["review_flags"]),
        "review_flag_counts": _multi(rows, "review_flags"), "words_min_median_max": _w(rows),
    }
    write_jsonl(rows, out_dir / "gold.jsonl")
    write_csv(rows, out_dir / "gold.csv")
    write_csv([{"gold_id": x["gold_id"], "text": x["text"], "sif_potential": x["sif_potential"], "lsr_raw": x["lsr_raw"],
                "energy_source_raw": x["energy_source_raw"], "flags": "|".join(x["review_flags"])} for x in rows if x["review_flags"]],
              out_dir / "review_queue.csv")
    write_json(stats, out_dir / "stats.json")
    log.info("gold: %d rows, %d need review (%s)", len(rows), stats["rows_with_review_flags"], stats["review_flag_counts"])
    return {"rows": rows, "stats": stats}


def _lsr(rows):
    c: dict = {}
    for r in rows:
        for l in r["life_saving_rules"] or ["(none)"]:
            c[l] = c.get(l, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def _multi(rows, field):
    c: dict = {}
    for r in rows:
        for v in r[field]:
            k = v.split(":")[0]
            c[k] = c.get(k, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def _w(rows):
    ws = sorted(r["words"] for r in rows)
    return [ws[0], ws[len(ws) // 2], ws[-1]] if ws else [0, 0, 0]


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run()
