"""
Gate-check a generated scope batch BEFORE it goes near training.

    python -m TRAINING.audit_scope_batch DATA/scope/negatives.jsonl

Counting distinct first-words and settings is not enough: a for-loop satisfies both perfectly.
These checks measure whether the text was WRITTEN or ASSEMBLED. The decisive one is n-gram
repetition - a template reuses phrases, a writer does not.

Exit code is non-zero on failure, so it can sit in front of prepare_scope_data.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

NGRAM = 6
LIMITS = {
    "ngram_reuse_rows": 2,      # no 6-word sequence may appear in more than N rows
    "min_mattr": 0.78,          # moving-average TTR, 50-word window. UNLIKE raw TTR this does
                                # not shrink with corpus size (Heaps' law), so one threshold works
                                # for a 30-row batch and a 3000-row file. Templates sit near 0.60.
    "max_doubled_pct": 0.08,    # mechanical "word word" artifact
    "max_near_dup": 2,
    "min_first_word_frac": 0.60,   # per-batch only - across many batches collisions are normal
                                   # and the generation prompt explicitly allows shared openers
}


def _words(t: str) -> list[str]:
    return re.findall(r"\w+", t.lower())


def audit(rows: list[dict]) -> tuple[dict, list[str]]:
    texts = [r.get("text", "") for r in rows]
    n = len(rows)
    fails: list[str] = []

    grams = Counter()
    for t in texts:
        w = _words(t)
        for i in range(len(w) - NGRAM + 1):
            grams[" ".join(w[i:i + NGRAM])] += 1
    worst = grams.most_common(1)[0] if grams else ("", 0)
    reused = {k: v for k, v in grams.items() if v > LIMITS["ngram_reuse_rows"]}

    allw = [x for t in texts for x in _words(t)]
    ttr = len(set(allw)) / max(1, len(allw))
    win = 50
    mattr = (sum(len(set(allw[i:i + win])) / win for i in range(max(1, len(allw) - win)))
             / max(1, len(allw) - win)) if len(allw) > win else ttr
    doubled = sum(1 for t in texts if re.search(r"\b(\w+)\s+\1\b", t, re.I))
    firsts = Counter((_words(t) or [""])[0] for t in texts)
    norm = Counter(" ".join(_words(t)) for t in texts)
    near_dup = sum(v - 1 for v in norm.values() if v > 1)

    bad_register = sum(1 for r in rows
                       if r.get("register") == "terse_two_words" and len(r.get("text", "").split()) > 8)

    m = {
        "rows": n,
        "reused_6grams": len(reused),
        "worst_6gram": worst[0][:60], "worst_6gram_rows": worst[1],
        "mattr_50": round(mattr, 3),
        "type_token_ratio": round(ttr, 3), "ttr_note": "falls with corpus size - read mattr_50",
        "doubled_word_rows": doubled, "doubled_word_pct": round(doubled / max(1, n), 3),
        "distinct_first_words": len(firsts), "first_word_frac": round(len(firsts) / max(1, n), 3),
        "exact_duplicates": near_dup,
        "register_length_mismatch": bad_register,
        "mean_words": round(len(allw) / max(1, n), 1),
        "kind": dict(Counter(r.get("kind") for r in rows)),
        "lang": dict(Counter(r.get("lang") for r in rows)),
        "settings": len({r.get("setting") for r in rows}),
    }

    if reused:
        fails.append(f"TEMPLATE: {len(reused)} six-word sequences repeat across rows "
                     f"(worst appears in {worst[1]} rows: '{worst[0][:50]}'). "
                     f"The text was assembled, not written.")
    if mattr < LIMITS["min_mattr"]:
        fails.append(f"LOW VOCABULARY: MATTR-50 {mattr:.3f} < {LIMITS['min_mattr']} - "
                     f"the same words are being recycled inside a short window.")
    if doubled / max(1, n) > LIMITS["max_doubled_pct"]:
        fails.append(f"MECHANICAL ARTIFACT: {doubled}/{n} rows carry a doubled word - "
                     f"a script applying the 'repeated word' rule, not a typo.")
    if near_dup > LIMITS["max_near_dup"]:
        fails.append(f"DUPLICATES: {near_dup} rows are identical after normalisation.")
    multi_batch = len({r.get("batch") for r in rows}) > 1
    if not multi_batch and len(firsts) / max(1, n) < LIMITS["min_first_word_frac"]:
        fails.append(f"REPETITIVE OPENINGS: only {len(firsts)} distinct first words in {n} rows.")
    if bad_register:
        fails.append(f"METADATA DRIFT: {bad_register} rows tagged terse_two_words run past 8 words - "
                     f"the labels were assigned independently of the text.")
    return m, fails


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="quality-gate a generated scope batch")
    ap.add_argument("path")
    ap.add_argument("--batch", help="audit only rows with this batch tag")
    a = ap.parse_args(argv)

    p = Path(a.path)
    if not p.exists():
        raise SystemExit(f"{p} not found")
    rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if a.batch:
        rows = [r for r in rows if r.get("batch") == a.batch]
    if not rows:
        raise SystemExit("no rows to audit")

    m, fails = audit(rows)
    print(json.dumps(m, indent=2, ensure_ascii=False))
    if fails:
        print(f"\nREJECT this batch - {len(fails)} problem(s):\n")
        for f in fails:
            print(f"  * {f}")
        print("\nRegenerate. Do not import it; a template teaches the gate to match the template.")
        return 1
    print("\nPASS - the batch reads as written text. Safe to import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
