"""
Relevance + sufficiency audit of the teacher seed pool for SIH26165 (Oil India SIF-precursor engine).

Answers two questions about DATA/Processed/unified/teacher_input.jsonl (and the wider corpus):
  1. Is it ENOUGH?      expected teacher yield vs the 12 000-row / per-verdict / per-language / GLiNER targets
  2. Is it RELEVANT?    oil & gas vocabulary, work domain, energy types, Life-Saving-Rule coverage,
                        precursor-vs-outcome balance, onshore/offshore, India context, language, length

    python -m CLEANING.audit_relevance            -> DATA/Processed/relevance_audit.md + relevance_audit.json
Read-only; runs in seconds.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "CLEANING"  # noqa: A001

from .clean_osha_abstracts import oilgas_score  # noqa: E402
from .config import PROCESSED_DIR  # noqa: E402
from .evaluate_readiness import _lang  # noqa: E402

TEACHER_INPUT = PROCESSED_DIR / "unified" / "teacher_input.jsonl"
CORPUS = PROCESSED_DIR / "unified" / "corpus.jsonl"
GOLD = PROCESSED_DIR / "gold" / "gold.jsonl"
OUT_MD = PROCESSED_DIR / "relevance_audit.md"
OUT_JSON = PROCESSED_DIR / "relevance_audit.json"

# ---- targets (mirror TRAINING/config.py so this module stays independent of it)
TARGET_TRAIN_ROWS = 12_000
VERDICT_QUOTA = {"EXPOSURE": 3000, "P_SIF": 2040, "LOW_ENERGY": 2040, "CAPACITY": 1800, "SUCCESS": 840,
                 "NON_EVENT": 720, "INSUFFICIENT": 720, "H_SIF": 480, "L_SIF": 360}
LANG_TARGET = {"hinglish": 0.45, "english": 0.35, "devanagari": 0.10, "assamese": 0.05, "other": 0.05}
GLINER_MIN_SPAN_ROWS = 1500
GENERATE_TOTAL_ROWS = 10000
REWIND_VARIANTS = 4
ACCEPT_RATE = {"generate": 0.80, "rewind": 0.75, "label": 0.85}     # conservative validator pass rates
SEED_SOURCE_CAPS: dict = {}
GEN_INDIC_SHARE = 0.60      # LANG_MIXES average (Hinglish + Devanagari + Assamese)
REW_INDIC_SHARE = 0.375     # Variant B always Hinglish/Assamese (1/4) + Variant A Devanagari on every 2nd seed (1/8)
try:  # keep in sync with the training package when it is present
    from TRAINING.config import GENERATE_TOTAL_ROWS as _G, SEED_SOURCE_CAPS as _C, TARGET_TRAIN_ROWS as _T, VERDICT_QUOTA as _V  # noqa: WPS433
    GENERATE_TOTAL_ROWS, TARGET_TRAIN_ROWS = _G, _T
    VERDICT_QUOTA = {k: (round(v * _T) if v <= 1 else v) for k, v in _V.items()}   # config stores fractions
    SEED_SOURCE_CAPS = dict(_C)
except Exception:  # noqa: BLE001
    pass

# ---- lexicons (English; the Hinglish/Devanagari share of the pool is measured separately)
DOMAIN = {
    "drilling_well": r"\b(drill(?:ing)? rig|rig floor|derrick|drill pipe|driller|roughneck|floor ?hand|tool ?pusher|workover|well ?head|well site|casing|tubing|mud pump|blowout|bop\b|kick\b|tripping|top drive|kelly|catwalk|wireline|coil(?:ed)? tubing|frac)",
    "production_process": r"\b(separator|gas plant|gathering station|ggs\b|ocs\b|compressor|processing plant|tank farm|storage tank|dehydration|flare|manifold|heater treater|pump ?jack|pumping unit|production facility|process unit|h2s|hydrogen sul[fp]hide)",
    "pipeline": r"\b(pipeline|right of way|row\b|sectionali[sz]ing valve|pig launcher|pigging|hot tap|scraper)",
    "refinery_petrochem": r"\b(refiner(?:y|ies)|petrochemical|crude unit|distillation|hydrocracker|catalyst|reformer|coker)",
    "marketing_lpg_pol": r"\b(lpg|bottling plant|tank truck|tanker|pol\b|petrol pump|retail outlet|depot|terminal|loading gantry|cylinder)",
    "construction_projects": r"\b(scaffold|excavat|trench|construction site|project site|rebar|concrete|formwork|crane|eot crane|hoist|welding|fabrication)",
    "transport_driving": r"\b(driver|driving|vehicle|truck|reversing|road accident|overturn|collision|forklift|haul(?:age|ing)? truck)",
    "mining": r"\b(mine\b|mining|underground|shaft|roof bolt|face\b|longwall|continuous miner|scoop|haulage|quarry|dragline|stope)",
    "marine_offshore": r"\b(vessel|offshore|platform|deck crew|gangway|mooring|anchor|diver|diving|rov\b|subsea|jack-?up|semi-?sub)",
    "electrical": r"\b(electrical|electric shock|electrocut|switchgear|kv\b|volts?|live (?:panel|wire|conductor)|arc flash|transformer|substation|cable laying)",
}
ENERGY = {
    "gravity": r"\b(fall|fell|height|dropped|drop(?:ped)? object|elevat|ladder|scaffold|roof|collapse|overhead|suspended load|from above)",
    "motion": r"\b(struck by|hit by|vehicle|truck|moving|swing|run over|ran over|collision|rotating|conveyor|forklift|crane)",
    "mechanical": r"\b(caught (?:in|between)|crush|pinch|amputat|entangle|rotating|tong|winch|gear|nip point|guard)",
    "electrical": r"\b(electr|shock|voltage|kv\b|live (?:panel|wire|line)|arc flash|energi[sz]ed)",
    "pressure": r"\b(pressure|hydraulic|pneumatic|blowout|kick\b|release|rupture|burst|hose whip|compressed)",
    "chemical": r"\b(h2s|hydrogen sul|toxic|chemical|acid|caustic|fumes|vapou?r|gas leak|inhal|asphyx|oxygen deficien|confined space)",
    "temperature_fire": r"\b(fire|flash|explo|burn|hot work|weld|ignit|steam|hot oil|flammable|thermal)",
    "sound_radiation_bio": r"\b(noise|radiation|radioactive|snake|insect|bite|heat stroke|heat stress)",
}
LSR = {
    "Working at Height": r"\b(height|scaffold|ladder|harness|fall arrest|edge protection|roof|elevated|lifeline|fall from)",
    "Line of Fire": r"\b(line of fire|struck by|caught between|crush|pinch|dropped object|suspended load|swing|run over|under the load)",
    "Energy Isolation": r"\b(loto|lock ?out|tag ?out|isolat|energi[sz]ed|de-?energi|zero energy|stored energy|live (?:panel|wire|line))",
    "Confined Space": r"\b(confined space|tank entry|vessel entry|manhole|entry permit|oxygen deficien|gas test)",
    "Hot Work": r"\b(hot work|weld|cutting torch|grind|flammable|ignition source|fire watch|gas free)",
    "Driving": r"\b(driver|driving|vehicle|seat ?belt|speed|reversing|journey|road|overturn|tank truck|forklift)",
    "Safe Mechanical Lifting": r"\b(crane|lift(?:ing)?|sling|rigging|hoist|load|banksman|winch|shackle|eot)",
    "Work Authorisation": r"\b(permit|ptw\b|jsa\b|risk assessment|toolbox|authori[sz]|work order|isolation certificate)",
    "Bypassing Safety Controls": r"\b(bypass|override|defeat|disabled|interlock|removed guard|guard (?:was )?removed|inhibit|tamper)",
}
INDIA = r"\b(india|oisd|assam|duliajan|digboi|arunachal|ongc|oil india|dgms|pngrb|pesos?|tank truck|ttpa|bottling plant|gail|iocl|hpcl|bpcl|crore|lakh|rupee)"
NEAR_MISS = r"\b(near[- ]miss|no injur|no one was (?:hurt|injured)|nobody was (?:hurt|injured)|narrowly|could have|potential(?:ly)? (?:fatal|serious)|uninjured|without injury|escaped)"
OUTCOME_SEVERE = r"\b(fatal|died|death|killed|amputat|fractur|hospitali|lost time|lti\b|permanent|disab|burn(?:s|ed)|unconscious)"
_RX = {k: re.compile(v, re.I) for k, v in {**DOMAIN, **ENERGY, **LSR}.items()}
_INDIA, _NM, _SEV = re.compile(INDIA, re.I), re.compile(NEAR_MISS, re.I), re.compile(OUTCOME_SEVERE, re.I)


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "n/a"


def _hits(rx: dict, text: str) -> list[str]:
    return [k for k, r in rx.items() if r.search(text)]


def audit_rows(rows: list[dict]) -> dict:
    n = len(rows)
    by_source: dict[str, dict] = defaultdict(lambda: {"n": 0, "oilgas": 0, "energy": 0, "india": 0, "near_miss": 0, "severe": 0,
                                                       "long": 0, "short": 0, "words": 0, "langs": Counter(), "domains": Counter(),
                                                       "record_type": Counter(), "job": Counter()})
    lsr_cov, energy_cov, domain_cov = Counter(), Counter(), Counter()
    multi_energy = 0
    for r in rows:
        text = (r.get("text") or "")
        ctx = r.get("context") or {}
        full = " ".join(str(v) for v in [text, ctx.get("what_went_wrong") or "", ctx.get("title") or ""] if v)
        src = r.get("source") or "?"
        b = by_source[src]
        b["n"] += 1
        b["job"][r.get("teacher_prompt") or "?"] += 1
        b["record_type"][r.get("record_type") or "?"] += 1
        w = len(text.split())
        b["words"] += w
        b["long"] += w > 300
        b["short"] += w < 15
        score, _terms = oilgas_score(full)
        b["oilgas"] += score >= 2
        e = _hits({k: _RX[k] for k in ENERGY}, full)
        b["energy"] += bool(e)
        multi_energy += len(e) > 1
        for k in e:
            energy_cov[k] += 1
        d = _hits({k: _RX[k] for k in DOMAIN}, full)
        for k in d:
            domain_cov[k] += 1
            b["domains"][k] += 1
        for k in _hits({k: _RX[k] for k in LSR}, full):
            lsr_cov[k] += 1
        b["india"] += bool(_INDIA.search(full))
        b["near_miss"] += bool(_NM.search(full))
        b["severe"] += bool(_SEV.search(full))
        b["langs"][_lang(text)] += 1
    out = {"rows": n, "by_source": {}, "lsr_keyword_coverage": dict(lsr_cov.most_common()),
           "energy_coverage": dict(energy_cov.most_common()), "domain_coverage": dict(domain_cov.most_common()),
           "multi_energy_rows": multi_energy}
    for src, b in sorted(by_source.items(), key=lambda kv: -kv[1]["n"]):
        m = b["n"]
        out["by_source"][src] = {
            "n": m, "job": dict(b["job"]), "record_type": dict(b["record_type"].most_common(6)),
            "oilgas_vocab": _pct(b["oilgas"], m), "energy_cue": _pct(b["energy"], m), "india_context": _pct(b["india"], m),
            "near_miss_like": _pct(b["near_miss"], m), "severe_outcome": _pct(b["severe"], m),
            "avg_words": round(b["words"] / max(1, m)), "over_300_words": _pct(b["long"], m), "under_15_words": _pct(b["short"], m),
            "language": dict(b["langs"].most_common(4)), "top_domains": dict(b["domains"].most_common(4)),
        }
    tot = Counter()
    for b in by_source.values():
        for k in ("oilgas", "energy", "india", "near_miss", "severe", "long"):
            tot[k] += b[k]
        tot["langs_english"] += b["langs"]["english"]
    out["totals"] = {k: _pct(v, n) for k, v in tot.items()}
    return out


def _capped(rows: list[dict], job: str) -> int:
    per = Counter(r["source"] for r in rows if r.get("teacher_prompt") == job)
    return sum(min(n, SEED_SOURCE_CAPS.get(src, n)) for src, n in per.items())


def sufficiency(rows: list[dict]) -> dict:
    rewind = _capped(rows, "rewind")
    label = _capped(rows, "label")
    y_gen = round(GENERATE_TOTAL_ROWS * ACCEPT_RATE["generate"])
    y_rew = round(rewind * REWIND_VARIANTS * ACCEPT_RATE["rewind"])
    y_lab = round(label * ACCEPT_RATE["label"])
    total = y_gen + y_rew + y_lab
    dedup_loss = round(total * 0.08)                       # near-duplicate + leakage guard (observed 5-10 %)
    usable = total - dedup_loss
    # language: rewind/label rows are in the seed language (English); Hinglish/Devanagari/Assamese come from
    # §1 generate (its lang_mix quota) and from the rewind prompt's language variants
    gen_indic = round(y_gen * GEN_INDIC_SHARE)
    rew_indic = round(y_rew * REW_INDIC_SHARE)
    indic = gen_indic + rew_indic
    need_indic = round(TARGET_TRAIN_ROWS * (LANG_TARGET["hinglish"] + LANG_TARGET["devanagari"] + LANG_TARGET["assamese"]))
    # verdict classes that seeds can NOT produce by themselves (need generate / label): LOW_ENERGY, NON_EVENT, SUCCESS
    return {
        "seeds_rewind": rewind, "rows_label": label, "source_caps": SEED_SOURCE_CAPS,
        "expected_accepted": {"generate": y_gen, "rewind": y_rew, "label": y_lab, "total": total, "after_dedup": usable},
        "target_train_rows": TARGET_TRAIN_ROWS, "meets_row_target": usable >= TARGET_TRAIN_ROWS,
        "gliner_span_rows": {"expected": usable, "min": GLINER_MIN_SPAN_ROWS, "ok": usable >= GLINER_MIN_SPAN_ROWS},
        "indic_language_rows": {"expected": indic, "needed": need_indic, "ok": indic >= need_indic,
                                "note": "raise GENERATE_TOTAL_ROWS or run `--job generate` a second pass if short"},
        "verdict_quota": VERDICT_QUOTA,
        "requests_estimate": {"generate": GENERATE_TOTAL_ROWS // 20, "rewind": -(-rewind // 3), "label": -(-label // 20)},
    }


def verdict(a: dict, s: dict) -> tuple[str, list[str]]:
    notes = []
    ok = s["meets_row_target"] and s["gliner_span_rows"]["ok"]
    t = a["totals"]
    def pnum(p): return int(p.rstrip("%")) if p != "n/a" else 0
    if pnum(t["oilgas"]) < 40:
        notes.append(f"only {t['oilgas']} of seed rows use explicit oil & gas vocabulary - the rest are generic industrial "
                     f"(MSHA mining, OSHA construction/manufacturing). The ENERGY types transfer (gravity, motion, mechanical, "
                     f"electrical, pressure); the vocabulary does not. Rewind prompt already re-sets each seed at an Oil India site, "
                     f"and §1 generate adds site-specific text - keep that, and prefer oil&gas / OISD / IADC seeds when quota is short.")
    if pnum(t["india"]) < 5:
        notes.append(f"India context in seeds is {t['india']} - it must come from OIL_CONTEXT in the prompts and the india_context trap "
                     f"quota; gold-180 is the only India-flavoured eval. Adding more OISD archive PDFs is the cheapest fix.")
    if pnum(t["langs_english"]) > 90:
        notes.append(f"seeds are {t['langs_english']} English; Hinglish / Devanagari / Assamese rows come entirely from generation - "
                     f"expected {s['indic_language_rows']['expected']} vs needed {s['indic_language_rows']['needed']} "
                     f"({'OK' if s['indic_language_rows']['ok'] else 'SHORT - raise GENERATE_TOTAL_ROWS'}).")
    thin = [k for k in LSR if a["lsr_keyword_coverage"].get(k, 0) < 150]
    if thin:
        notes.append(f"few seeds even mention these Life-Saving Rules: {', '.join(thin)} - set a generate quota for them.")
    if pnum(t["near_miss"]) < 25:
        notes.append(f"only {t['near_miss']} of seeds read as near-miss / no-injury; most are post-injury reports. "
                     f"§2 rewind (variants A/B/C stop the event before injury) is what converts them into precursors - "
                     f"so the rewind job is NOT optional.")
    if pnum(t["long"]) > 20:
        notes.append(f"{t['long']} of seeds exceed 300 words - the runner sends a compact record; fine for rewind, "
                     f"but label rows longer than 380 tokens are truncated.")
    status = "ENOUGH_AND_RELEVANT" if ok and len(notes) <= 3 else "ENOUGH_WITH_GAPS" if ok else "NOT_ENOUGH"
    return status, notes


def _md(a: dict, s: dict, status: str, notes: list[str], gold_n: int) -> str:
    L = [f"# Seed-pool relevance & sufficiency audit", "", f"**Status: {status}**", ""]
    for nte in notes:
        L.append(f"- {nte}")
    L += ["", "## 1. Is it enough?", "",
          f"- seeds after per-source caps {s['source_caps']}: {s['seeds_rewind']} rewind + {s['rows_label']} label rows; generate target {GENERATE_TOTAL_ROWS}",
          f"- expected accepted teacher rows: generate {s['expected_accepted']['generate']} + rewind {s['expected_accepted']['rewind']} + label {s['expected_accepted']['label']} = {s['expected_accepted']['total']} → after dedup ≈ **{s['expected_accepted']['after_dedup']}** vs target {TARGET_TRAIN_ROWS} → {'OK' if s['meets_row_target'] else 'SHORT'}",
          f"- GLiNER span rows: every accepted row carries spans → {s['gliner_span_rows']['expected']} ≥ {GLINER_MIN_SPAN_ROWS} → OK",
          f"- Indic-language rows (Hinglish+Devanagari+Assamese target 60 %): expected ≈ {s['indic_language_rows']['expected']} vs needed {s['indic_language_rows']['needed']} → {'OK' if s['indic_language_rows']['ok'] else 'SHORT'}",
          f"- API requests: generate {s['requests_estimate']['generate']}, rewind {s['requests_estimate']['rewind']}, label {s['requests_estimate']['label']}",
          f"- eval: gold-180 ({gold_n} rows) + IHM 425 + contrast set — held out, never seeds", "",
          "## 2. Is it relevant?  (per source)", "",
          "| source | rows | job | oil&gas vocab | energy cue | India ctx | near-miss-like | severe outcome | avg words | >300 w | top domains | language |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for src, b in a["by_source"].items():
        L.append(f"| {src} | {b['n']} | {','.join(b['job'])} | {b['oilgas_vocab']} | {b['energy_cue']} | {b['india_context']} | {b['near_miss_like']} | {b['severe_outcome']} | {b['avg_words']} | {b['over_300_words']} | {', '.join(f'{k} {v}' for k, v in b['top_domains'].items())} | {', '.join(f'{k} {v}' for k, v in b['language'].items())} |")
    t = a["totals"]
    L += ["", f"Totals: oil&gas vocab {t['oilgas']} · energy cue {t['energy']} · India {t['india']} · near-miss-like {t['near_miss']} · severe {t['severe']} · English {t['langs_english']} · >300 words {t['long']}", "",
          "## 3. Coverage across the seed pool (keyword-implied, not labels)", "",
          "| Life-Saving Rule | seeds mentioning it |", "|---|---|"]
    for k in LSR:
        L.append(f"| {k} | {a['lsr_keyword_coverage'].get(k, 0)} |")
    L += ["", "| energy type | seeds |", "|---|---|"]
    for k, v in a["energy_coverage"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "| work domain | seeds |", "|---|---|"]
    for k, v in a["domain_coverage"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## 4. Verdict quota the teacher must fill", "", "| verdict | rows | mainly from |", "|---|---|---|"]
    src_hint = {"EXPOSURE": "rewind A/B (event stopped before release)", "P_SIF": "rewind + generate", "LOW_ENERGY": "generate + label (OSHA SIR low severity, MSHA no-injury)",
                "CAPACITY": "rewind C (control present but weak) + generate", "SUCCESS": "generate + rewind (control worked)", "NON_EVENT": "generate (observations, training, hypotheticals)",
                "INSUFFICIENT": "generate (vague one-liners) + register", "H_SIF": "original fatal seeds (IOGP, OISD, MSHA fatal)", "L_SIF": "original LTI/RWC seeds (OSHA SIR, IADC)"}
    for k, v in VERDICT_QUOTA.items():
        L.append(f"| {k} | {v} | {src_hint[k]} |")
    return "\n".join(L) + "\n"


def main() -> int:
    rows = _read(TEACHER_INPUT)
    if not rows:
        print(f"{TEACHER_INPUT} missing - run the pipeline first")
        return 1
    a = audit_rows(rows)
    s = sufficiency(rows)
    status, notes = verdict(a, s)
    gold_n = len(_read(GOLD))
    md = _md(a, s, status, notes, gold_n)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"status": status, "notes": notes, "audit": a, "sufficiency": s}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
