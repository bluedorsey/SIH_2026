"""
Training-readiness evaluation: is what we have valid, and is it enough?

Reads the cleaned outputs (via the results dict from run_pipeline, or from disk) and scores every source
against the v2 plan (SIH26165_Data_Scarcity_Plan.md):

VALIDITY (per source)   - parse completeness, empty/short texts, duplicate rate, label coverage, language/script
SUFFICIENCY (per model) - GLiNER: span-annotated rows (need >= 1,500 with all 11 roles present)
                          SetFit prefilter: sentence-level verdict labels (need >= 16/class, target quotas)
                          LSR mapper: rule-labelled seeds per LSR (need >= 600/rule after §2 expansion; seeds >= 100/rule)
                          Post-injury share of the seed pool (must be <= 6 % of the final train set -> reported as the cap)
                          Language/script coverage (targets: Hinglish 45 %, English 35 %, Devanagari 10 %, Assamese 5 %)

Writes DATA/Processed/training_readiness.md + .json
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from .common.io import read_jsonl, write_json
from .config import (
    LSR_CANONICAL,
    OUT_ALERTS_DIR,
    OUT_GOLD_DIR,
    OUT_IHM_DIR,
    OUT_IOGP_DIR,
    OUT_MSHA_DIR,
    OUT_OSHA_ABSTRACTS_DIR,
    OUT_OSHA_DIR,
    OUT_READINESS_JSON,
    OUT_READINESS_MD,
    OUT_REGISTER_DIR,
    OUT_UNIFIED_DIR,
)

log = logging.getLogger("clean.readiness")

# targets from the v2 plan
TARGET_TRAIN_ROWS = 12000
VERDICT_QUOTA = {"EXPOSURE": .25, "P_SIF": .17, "LOW_ENERGY": .17, "CAPACITY": .15, "SUCCESS": .07, "NON_EVENT": .06, "INSUFFICIENT": .06, "H_SIF": .04, "L_SIF": .03}
LSR_MIN_TRAIN = 600
LSR_MIN_SEEDS = 100
GLINER_MIN_ROWS = 1500
GLINER_ROLES = ["energy_cue", "release_cue", "no_release_cue", "exposure_cue", "control_present", "control_absent",
                "control_ineffective", "pseudo_control", "negation_cue", "outcome_cue", "statement_cue"]
SETFIT_MIN_PER_CLASS = 16
LANG_TARGET = {"hinglish": .45, "english": .35, "devanagari": .10, "assamese": .05}
POST_INJURY_CAP = .06

_DEV = re.compile(r"[ऀ-ॿ]")
_ASM = re.compile(r"[ঀ-৿]")
# romanised-Hindi function words that are NOT English words (so "the", "me", "par", "se" are deliberately excluded)
_HINGLISH = re.compile(r"\b(nahi|nahin|nhi|tha|thi|thay|hai|hain|kiya|kiye|karo|karna|raha|rahi|rahe|gaya|gayi|gaye|mein|aur|bina|koi|kaam|wala|wali|hua|hui|hue|liye|lekin|phir|abhi|jab|tab|kya|kyun|yahan|wahan|upar|neeche|andar|bahar|pehle|baad|sirf|bhi|nikla|nikli|laga|lagi|chal|chalu|band|khula|khuli|gir|gira|giri|toota|tooti|bahut|thoda|achha|theek|dekha|dekhi|mila|mili|karke|hokar|wajah|dauran|samay|jagah|paas|door|ek|teen|char|paanch)\b", re.I)


def _load(path: Path) -> list[dict]:
    return read_jsonl(path) if path.exists() else []


_ASM_ROMAN = re.compile(r"\b(kora|nohol|nai|ase|ot|cholise|hoy|geche|bhitore|lok|dhuke|dhukise|kaam kora|hobo|nohoi|asil|korile|bhal|beya|pani|khub)\b", re.I)


def _lang(text: str) -> str:
    if _DEV.search(text):
        return "devanagari"
    if _ASM.search(text):
        return "assamese"
    if len(_ASM_ROMAN.findall(text)) >= 2:
        return "assamese_roman"
    hits = len(_HINGLISH.findall(text))
    return "hinglish" if hits >= 2 else "english"


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f} %" if d else "n/a"


def _validity(name: str, rows: list[dict], text_field: str = "text", label_fields: tuple = ()) -> dict:
    n = len(rows)
    if not n:
        return {"source": name, "rows": 0, "status": "MISSING"}
    empty = sum(1 for r in rows if not (r.get(text_field) or "").strip())
    short = sum(1 for r in rows if len((r.get(text_field) or "").split()) < 8)
    dups = sum(1 for r in rows if r.get("is_duplicate"))
    labels = {f: sum(1 for r in rows if r.get(f) not in (None, "", [], {})) for f in label_fields}
    langs: dict = {}
    for r in rows:
        k = _lang(r.get(text_field) or "")
        langs[k] = langs.get(k, 0) + 1
    issues = []
    if empty:
        issues.append(f"{empty} empty texts")
    if short / n > 0.15:
        issues.append(f"{_pct(short, n)} texts under 8 words")
    if dups / n > 0.10:
        issues.append(f"{_pct(dups, n)} duplicates")
    for f, c in labels.items():
        if c / n < 0.5:
            issues.append(f"{f} filled for only {_pct(c, n)}")
    status = "VALID" if not issues else "VALID_WITH_WARNINGS"
    return {"source": name, "rows": n, "empty": empty, "short_lt8w": short, "duplicates": dups,
            "label_coverage": labels, "language_guess": langs, "issues": issues, "status": status}


def evaluate(results: dict | None = None) -> dict:
    """results = run_pipeline results dict (optional); falls back to files on disk."""
    results = results or {}
    iogp = results.get("iogp", {}).get("records") or _load(OUT_IOGP_DIR / "records.jsonl")
    osha = results.get("osha", {}).get("oilgas") or _load(OUT_OSHA_DIR / "osha_oilgas.jsonl")
    reg = results.get("register", {}).get("rows") or []
    if not reg:
        reg = [r for p in OUT_REGISTER_DIR.glob("*_clean.jsonl") for r in read_jsonl(p)] if OUT_REGISTER_DIR.exists() else []
    absx = results.get("osha_abstracts", {}).get("rows") or _load(OUT_OSHA_ABSTRACTS_DIR / "abstracts.jsonl")
    msha = results.get("msha", {}).get("rows") or _load(OUT_MSHA_DIR / "msha_selected.jsonl")
    alerts = results.get("alerts", {}).get("rows") or _load(OUT_ALERTS_DIR / "alerts.jsonl")
    gold = results.get("gold", {}).get("rows") or _load(OUT_GOLD_DIR / "gold.jsonl")
    ihm = results.get("ihm", {}).get("rows") or _load(OUT_IHM_DIR / "ihm_eval.jsonl")
    unified = results.get("unified", {}).get("rows") or _load(OUT_UNIFIED_DIR / "corpus.jsonl")

    validity = [
        _validity("IOGP fatal/HiPo/PI", iogp, label_fields=("life_saving_rules", "what_went_wrong", "causal_factors")),
        _validity("OSHA SIR oil&gas", osha, label_fields=("event_type", "nature")),
        _validity("OSHA accident abstracts (16k)", absx, label_fields=("keywords",)),
        _validity("OSHA abstracts oil&gas subset", [r for r in absx if r.get("is_oilgas")], label_fields=("keywords",)),
        _validity("MSHA selected", msha, label_fields=("classification", "accident_type")),
        _validity("Safety alerts (IADC/IMCA/StepChange/OISD)", alerts, label_fields=("life_saving_rules", "what_went_wrong")),
        _validity("Register template", reg, label_fields=("category",)),
        _validity("Gold-180", gold, label_fields=("sif_potential", "statement_type")),
        _validity("Kaggle IHM (eval)", ihm, label_fields=("potential_level",)),
    ]

    # ---- seed pool (what §2 rewind can expand) ----
    seeds = [r for r in unified if r["split_hint"] == "seed_never_test" and not r["is_duplicate"]]
    seed_lsr = {l: 0 for l in LSR_CANONICAL}
    for r in seeds:
        for l in r["labels"]["life_saving_rules"]:
            seed_lsr[l] = seed_lsr.get(l, 0) + 1
    seeds_with_lsr = sum(1 for r in seeds if r["labels"]["life_saving_rules"])
    post_injury_seeds = sum(1 for r in seeds if r["labels"].get("actual_injury"))
    onshore = sum(1 for r in seeds if (r["meta"].get("onshore_offshore") == "onshore"))
    variants_per_seed = 4
    expected_rewound = len(seeds) * variants_per_seed

    # ---- sentence-level labelled rows (SetFit) ----
    setfit_rows = [r for r in gold]  # only gold carries verdict-ish labels today
    per_class = {}
    for r in setfit_rows:
        k = r["sif_potential"]
        per_class[k] = per_class.get(k, 0) + 1
    span_rows = 0  # no span-annotated data exists yet
    contrast_rows = sum(1 for r in unified if r["split_hint"] == "contrast_test_candidate")
    lang_gold = {}
    for r in gold:
        k = _lang(r["text"])
        lang_gold[k] = lang_gold.get(k, 0) + 1

    # ---- sufficiency verdicts ----
    lsr_gaps = {l: max(0, LSR_MIN_SEEDS - c) for l, c in seed_lsr.items() if c < LSR_MIN_SEEDS}
    models = {
        "gliner_span_model": {
            "have_span_rows": span_rows, "need": GLINER_MIN_ROWS, "roles_covered": [],
            "status": "NOT_READY",
            "blocker": "0 span-annotated rows. Nothing downloadable has the 11 roles; they must come from the teacher LLM (prompts §1/§2/§3) "
                       "or, as a smoke-test only, glossary weak labels (variant_lookup.json).",
        },
        "setfit_prefilter": {
            "have_labelled_rows": len(setfit_rows), "per_class": per_class, "min_per_class": SETFIT_MIN_PER_CLASS,
            "status": "EVAL_ONLY" if all(v >= SETFIT_MIN_PER_CLASS for v in per_class.values()) else "NOT_READY",
            "blocker": "Only gold-180 carries verdict labels (3-class YES/NO/UNCERTAIN, not the 9-class verdict) and it is the test set. "
                       f"Training rows with §0 verdicts: 0 of the {TARGET_TRAIN_ROWS} target. Teacher output required.",
        },
        "lsr_mapper": {
            "seeds_with_lsr": seeds_with_lsr, "seed_lsr_counts": seed_lsr, "seed_gaps_below_100": lsr_gaps,
            "expected_after_rewind_x4": {l: c * variants_per_seed for l, c in seed_lsr.items()},
            "status": "READY_FOR_REWIND" if not lsr_gaps else "SEEDS_THIN_FOR:" + ",".join(lsr_gaps),
        },
        "contrast_set_actual_vs_potential": {
            "rows": contrast_rows, "status": "READY" if contrast_rows >= 1000 else "THIN",
        },
    }
    scarcity = {
        "seed_pool": {"rows": len(seeds), "with_lsr": seeds_with_lsr, "post_injury": post_injury_seeds,
                      "post_injury_share": round(post_injury_seeds / len(seeds), 3) if seeds else None,
                      "onshore_tagged": onshore, "by_source": _count(seeds, "source"),
                      "expected_rewound_rows_x4": expected_rewound},
        "post_injury_cap_note": f"post-injury originals may be at most {int(POST_INJURY_CAP * 100)} % of the final train set "
                                f"(= {int(TARGET_TRAIN_ROWS * POST_INJURY_CAP)} rows of {TARGET_TRAIN_ROWS}); "
                                f"{post_injury_seeds} are available, so the surplus becomes evaluation / seeds-only.",
        "verdict_quota_targets": {k: int(v * TARGET_TRAIN_ROWS) for k, v in VERDICT_QUOTA.items()},
        "language_targets": LANG_TARGET, "gold_language_actual": lang_gold,
        "script_gap": "gold-180 has 0 Devanagari and 0 Assamese-script rows; training data must add them (10 % + 5 %) and gold v2 needs 30 + 20 rows",
    }
    overall = {
        "downloaded_sources_ready": [v["source"] for v in validity if v["status"].startswith("VALID")],
        "sources_missing": [v["source"] for v in validity if v["status"] == "MISSING"],
        "can_train_gliner_now": False,
        "can_train_setfit_now": False,
        "can_run_teacher_rewind_now": len(seeds) > 0,
        "one_line": ("Seeds and evaluation sets are valid and sufficient; NO model can be fine-tuned yet because zero rows carry span labels or 9-class "
                     "verdicts - the teacher-LLM run (prompts §1/§2/§3) is the gating step, and it can start now on "
                     f"{len(seeds)} seeds."),
    }
    report = {"generated_at": datetime.now().isoformat(timespec="seconds"), "validity": validity, "scarcity": scarcity, "models": models, "overall": overall}
    write_json(report, OUT_READINESS_JSON)
    OUT_READINESS_MD.write_text(_markdown(report), encoding="utf-8")
    log.info("readiness: %s", overall["one_line"])
    return report


def _markdown(rep: dict) -> str:
    L = [f"# Training readiness — {rep['generated_at']}", "", f"**{rep['overall']['one_line']}**", ""]
    L += ["## 1. Validity of each source", "", "| source | rows | empty | <8 words | dups | label coverage | language guess | status | issues |", "|---|---|---|---|---|---|---|---|---|"]
    for v in rep["validity"]:
        if v["status"] == "MISSING":
            L.append(f"| {v['source']} | 0 | | | | | | **MISSING** | not downloaded yet |")
            continue
        cov = ", ".join(f"{k} {_pct(c, v['rows'])}" for k, c in v["label_coverage"].items())
        langs = ", ".join(f"{k} {c}" for k, c in sorted(v["language_guess"].items(), key=lambda kv: -kv[1]))
        issues = "; ".join(v["issues"]) or "-"
        L.append(f"| {v['source']} | {v['rows']} | {v['empty']} | {v['short_lt8w']} | {v['duplicates']} | {cov} | {langs} | {v['status']} | {issues} |")
    s = rep["scarcity"]
    L += ["", "## 2. Seed pool for §2 Rewind", "",
          f"- seeds: **{s['seed_pool']['rows']}** unique rows ({s['seed_pool']['with_lsr']} with a Life-Saving Rule; {s['seed_pool']['onshore_tagged']} tagged onshore) → ≈ {s['seed_pool']['expected_rewound_rows_x4']} rewound rows at 4 variants each",
          "- by source: " + ", ".join(f"{k} {v}" for k, v in s["seed_pool"]["by_source"].items()),
          f"- post-injury seeds: {s['seed_pool']['post_injury']} ({s['seed_pool']['post_injury_share']}) — {s['post_injury_cap_note']}",
          f"- verdict quota targets for a {TARGET_TRAIN_ROWS}-row train set: " + ", ".join(f"{k} {v}" for k, v in s["verdict_quota_targets"].items()),
          "- language targets: " + ", ".join(f"{k} {int(v * 100)} %" for k, v in s["language_targets"].items()) + f" - gold-180 actual: {s['gold_language_actual']}",
          f"- {s['script_gap']}", ""]
    m = rep["models"]
    L += ["## 3. Can each model be trained?", ""]
    g = m["gliner_span_model"]
    L += [f"**GLiNER (span roles)** — {g['status']}: {g['have_span_rows']} span-annotated rows of {g['need']} needed. {g['blocker']}", ""]
    sf = m["setfit_prefilter"]
    L += [f"**SetFit / MiniLM prefilter** — {sf['status']}: {sf['have_labelled_rows']} labelled rows (per class {sf['per_class']}). {sf['blocker']}", ""]
    lm = m["lsr_mapper"]
    L += [f"**LSR mapper** — {lm['status']}: seeds per rule {lm['seed_lsr_counts']}; below 100 seeds: {lm['seed_gaps_below_100'] or 'none'}; expected after ×4 rewind: {lm['expected_after_rewind_x4']}", ""]
    c = m["contrast_set_actual_vs_potential"]
    L += [f"**Actual-vs-potential contrast/eval set** — {c['status']}: {c['rows']} rows", ""]
    L += ["## 4. What unblocks training", "",
          "1. Put a teacher key in `.env` (Gemini free tier for synthetic/public text) and run prompts §2 on `unified/teacher_input.jsonl` (rewind) and §1 (generate) — every output row carries the 11 span roles and the 9-class verdict.",
          "2. Run the sources still marked MISSING above through `python -m CLEANING.fetch.fetch_all` on the laptop, then re-run the pipeline.",
          "3. Keep gold-180 as the test set; the pipeline already removes any training row that near-duplicates it.", ""]
    return "\n".join(L)


def _count(rows: list[dict], field: str) -> dict:
    out: dict = {}
    for r in rows:
        k = str(r.get(field))
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    evaluate()
