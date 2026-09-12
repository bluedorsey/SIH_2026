"""
Weak span labels for GLiNER warm-up (NO API calls, seconds on CPU).

Matches the cleaned glossary (DATA/Processed/terms/glossary_clean.json: term + variants -> safety_signal role)
plus a small built-in cue lexicon against the unified corpus, and writes GLiNER-format rows:

    DATA/distilled/gliner/weak_train.json      [{"tokenized_text": [...], "ner": [[s, e, "energy source"], ...], "weak": true}]
    DATA/distilled/gliner/weak_stats.json

Use it ONLY as extra training rows behind the teacher-labelled data
(`python -m TRAINING.finetune.prepare_gliner_data --weak`), never for dev/test - the labels are lexical,
not contextual ("no injury" is tagged no_release_cue even inside a hypothetical sentence).

    python -m TRAINING.weak_label_gliner                 # teacher_input.jsonl (2.5k rows) -> weak_train.json
    python -m TRAINING.weak_label_gliner --source unified --limit 8000   # wider corpus
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "TRAINING"  # noqa: A001

from .config import DISTILLED_DIR, GLOSSARY_LOOKUP, MAX_SPAN_TOKENS, PROCESSED_DIR, ROLE_TO_GLINER_LABEL, ROLES, TEACHER_INPUT  # noqa: E402
from .finetune.tokenization import char_span_to_tokens, tokenize  # noqa: E402

log = logging.getLogger("weak_label")
OUT_DIR = DISTILLED_DIR / "gliner"
GLOSSARY_CLEAN = GLOSSARY_LOOKUP.parent / "glossary_clean.json"
UNIFIED = PROCESSED_DIR / "unified" / "corpus.jsonl"

# Built-in cue lexicon (role -> phrases).  Short, high-precision, English + Hinglish.
CUES: dict[str, list[str]] = {
    "negation_cue": ["no", "not", "without", "never", "nahi", "nahin", "na", "bina", "bagair", "failed to", "did not", "didn't", "wasn't", "was not", "nai"],
    "no_release_cue": ["near miss", "near-miss", "no injury", "no injuries", "no one was hurt", "nobody was injured", "narrowly missed", "narrowly avoided",
                       "no damage", "koi chot nahi", "kisi ko chot nahi", "bach gaya", "bach gaye", "did not fall", "did not release", "no contact", "was uninjured"],
    "release_cue": ["fell", "fell from", "struck", "struck by", "hit by", "caught between", "crushed", "exploded", "explosion", "electrocuted", "shock",
                    "flash", "arc flash", "gir gaya", "gir gayi", "lag gaya", "collapsed", "overturned", "rolled over", "ignited", "caught fire", "released", "blowout", "kick"],
    "outcome_cue": ["fatality", "fatal", "died", "death", "killed", "fracture", "fractured", "amputation", "amputated", "lost time injury", "lti",
                    "restricted work", "rwc", "medical treatment", "mtc", "first aid", "hospitalised", "hospitalized", "burns", "burn", "unconscious",
                    "maut", "mar gaya", "haddi toot gayi", "sprain", "bruise", "laceration", "scratch", "cut"],
    "energy_cue": ["height", "elevation", "fall from height", "working at height", "scaffold", "scaffolding", "high pressure", "pressure", "psi", "bar",
                   "kv", "volts", "live panel", "live wire", "energised", "energized", "h2s", "hydrogen sulphide", "hydrogen sulfide", "gas leak",
                   "hot work", "crane", "lifting", "suspended load", "load", "vehicle", "truck", "forklift", "reversing", "confined space", "tank",
                   "vessel", "well", "rig", "derrick", "mast", "rotating", "tong", "drill pipe", "casing", "chemical", "acid", "steam", "hot oil",
                   "temperature", "flammable", "fire", "kh", "unchai", "uchai", "current", "bijli", "electric", "electrical", "excavation", "trench"],
    "control_absent": ["no harness", "without harness", "no loto", "without loto", "no permit", "without permit", "no isolation", "not isolated",
                       "no gas test", "without gas test", "no barricade", "no barrier", "no ppe", "without ppe", "no helmet", "no spotter", "no banksman",
                       "harness nahi", "permit nahi", "loto nahi", "isolation nahi", "guard removed", "unguarded", "guard was missing", "no lockout",
                       "not tagged", "no tag", "bina harness", "bina permit", "no lifeline"],
    "control_present": ["harness attached", "harness was attached", "tied off", "anchored", "loto applied", "locked out", "isolated and locked",
                        "isolation confirmed", "permit in place", "permit was valid", "gas test done", "gas tested", "barricaded", "guarded", "spotter present",
                        "banksman present", "fall arrest", "lifeline connected", "zero energy verified", "tagged out", "loto laga", "permit tha", "harness laga tha"],
    "control_ineffective": ["harness not anchored", "harness not attached", "not tied off", "anchor point failed", "loto not verified", "isolation not verified",
                            "wrong isolation", "permit expired", "expired permit", "gas test expired", "barricade removed", "barricade breached", "bypassed",
                            "overridden", "defeated", "interlock bypassed", "alarm ignored", "not certified", "uncertified", "sling damaged", "damaged sling",
                            "wrong sling", "overloaded", "harness tha par", "loto laga tha par"],
    "pseudo_control": ["toolbox talk", "tbt", "training", "trained", "briefed", "briefing", "reminded", "warned", "instructed", "counselled", "counseled",
                       "experienced", "careful", "cautious", "be careful", "awareness", "signage", "sign board", "helmet", "gloves", "safety shoes", "goggles",
                       "ppe was worn", "wearing ppe", "samjhaya", "training di", "dhyan"],
    "exposure_cue": ["line of fire", "in the line of fire", "under the load", "under suspended load", "standing under", "within", "close to", "near the edge",
                     "at the edge", "leaning over", "reached into", "hand in", "hand inside", "between the", "beneath", "inside the tank", "entered the",
                     "unprotected edge", "open hole", "open flange", "neeche khada", "paas khada", "andar gaya", "haath andar"],
    "statement_cue": ["could have", "would have", "might have", "may have", "if", "agar", "had it", "potential", "worst case", "hypothetically", "last year",
                      "in 2019", "in 2020", "in 2021", "in 2022", "previously", "earlier incident", "recalled", "training scenario", "for training",
                      "mock drill", "drill", "closed", "completed", "rectified", "repaired", "replaced", "action taken", "corrective action", "ho sakta tha"],
}
# glossary safety_signal values that should not be trusted as spans (too generic)
GENERIC_SKIP = {"none", None, ""}
_NEG_IN = re.compile(r"\b(nahi|nahin|nhi|na|no|not|without|bina|bagair|missing|absent|removed)\b", re.I)


def _compile(phrases: list[str]) -> re.Pattern:
    phrases = sorted({p.strip() for p in phrases if p and p.strip()}, key=len, reverse=True)
    return re.compile(r"(?<![\wऀ-ॿঀ-৿])(?:" + "|".join(re.escape(p) for p in phrases) + r")(?![\wऀ-ॿঀ-৿])", re.I)


def build_lexicon() -> dict[str, re.Pattern]:
    role_phrases: dict[str, list[str]] = {r: list(v) for r, v in CUES.items()}
    n_gloss = 0
    if GLOSSARY_CLEAN.exists():
        for e in json.loads(GLOSSARY_CLEAN.read_text(encoding="utf-8")):
            role = e.get("safety_signal")
            if role in GENERIC_SKIP or role not in ROLES:
                continue
            for v in [e.get("term"), *(e.get("variants") or [])]:
                if v and 2 <= len(v) <= 60:
                    # glossary lists negated variants under the control term ("LOTO nahi kiya" under LOTO/control_present)
                    r = "control_absent" if role == "control_present" and _NEG_IN.search(v) else role
                    role_phrases.setdefault(r, []).append(v)
                    n_gloss += 1
    else:
        log.warning("%s not found - only the built-in cue lexicon is used (run CLEANING first)", GLOSSARY_CLEAN)
    log.info("lexicon: %d glossary variants + built-in cues", n_gloss)
    return {r: _compile(p) for r, p in role_phrases.items() if p}


# precedence when two roles overlap on the same characters: longer match wins, then this order
PRIORITY = ["control_ineffective", "control_absent", "control_present", "pseudo_control", "no_release_cue", "release_cue", "outcome_cue",
            "exposure_cue", "energy_cue", "statement_cue", "negation_cue"]


def weak_spans(text: str, lex: dict[str, re.Pattern]) -> list[tuple[int, int, str]]:
    found = []
    for role, pat in lex.items():
        for m in pat.finditer(text):
            found.append((m.start(), m.end(), role))
    # negation inside a longer control_absent / no_release span is redundant -> drop overlaps by (length desc, priority)
    found.sort(key=lambda t: (-(t[1] - t[0]), PRIORITY.index(t[2]) if t[2] in PRIORITY else 99))
    taken: list[tuple[int, int, str]] = []
    for s, e, role in found:
        if any(not (e <= ts or s >= te) for ts, te, _ in taken):
            continue
        taken.append((s, e, role))
    return sorted(taken)


def _iter_source(name: str, limit: int) -> list[dict]:
    path = TEACHER_INPUT if name == "teacher_input" else UNIFIED
    if not path.exists():
        raise SystemExit(f"{path} missing - run `python -m CLEANING.run_pipeline` first")
    rows = [json.loads(ln) for ln in open(path, "r", encoding="utf-8") if ln.strip()]
    if name == "unified":
        rows = [r for r in rows if r.get("split_hint") not in ("eval_only", "gold_test", "contrast_test_candidate") and not r.get("is_duplicate")]
    random.Random(13).shuffle(rows)
    return rows[:limit] if limit else rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["teacher_input", "unified"], default="teacher_input")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-spans", type=int, default=2, help="keep only texts with at least this many weak spans")
    ap.add_argument("--max-tokens", type=int, default=380)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    lex = build_lexicon()
    out, by_role, kept, skipped_long, skipped_few = [], Counter(), 0, 0, 0
    for r in _iter_source(a.source, a.limit):
        text = (r.get("text") or "").strip()
        if not text:
            continue
        toks = tokenize(text)
        if len(toks) > a.max_tokens or len(toks) < 6:
            skipped_long += 1
            continue
        ner = []
        for s, e, role in weak_spans(text, lex):
            ts, te = char_span_to_tokens(toks, s, e)
            if ts is None or te - ts + 1 > MAX_SPAN_TOKENS:
                continue
            ner.append([ts, te, ROLE_TO_GLINER_LABEL[role]])
            by_role[role] += 1
        if len(ner) < a.min_spans:
            skipped_few += 1
            continue
        out.append({"tokenized_text": [t[0] for t in toks], "ner": ner, "id": r.get("id") or r.get("uid") or f"weak_{kept}",
                    "seed_id": r.get("id") or r.get("uid"), "verdict": None, "lang": (r.get("meta") or {}).get("language") or r.get("language") or "en", "weak": True})
        kept += 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "weak_train.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    stats = {"source": a.source, "rows": kept, "spans": sum(by_role.values()), "by_role": dict(by_role.most_common()),
             "skipped_too_long_or_short": skipped_long, "skipped_too_few_spans": skipped_few}
    (OUT_DIR / "weak_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    log.info("weak rows %d, spans %d -> %s", kept, stats["spans"], OUT_DIR / "weak_train.json")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
