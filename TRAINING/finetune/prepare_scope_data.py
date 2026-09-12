"""
Build the in-scope / out-of-scope dataset for the scope gate.

    python -m TRAINING.finetune.prepare_scope_data
    python -m TRAINING.finetune.prepare_scope_data --negatives DATA/scope/negatives.jsonl

POSITIVES (in_scope = 1) come from the existing distilled corpus - every row there is a safety
observation, LOW_ENERGY and NON_EVENT included. A minor safety issue is still a safety issue;
"is it severe enough" is a DIFFERENT question, answered by the prefilter head, and conflating
the two is what gave prefilter recall_sif 0.75 and made it unusable as a gate.

NEGATIVES (in_scope = 0) come from DATA/scope/negatives.jsonl - the generated file, one JSON
object per line: {"text", "label", "kind", "lang", ...}. Rows with label 1 in that file are the
mirror positives (domestic vocabulary, real hazard) and are added to the POSITIVE side.

Out -> DATA/scope/{train,dev,test}.jsonl + stats.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.finetune"  # noqa: A001

from ..config import DATA_DIR, DISTILLED_DIR, DISTILLED_RAW_DIR  # noqa: E402

SETFIT_DATA = DISTILLED_DIR / "setfit"
SCOPE_DIR = DATA_DIR / "scope"
NEGATIVES = SCOPE_DIR / "negatives.jsonl"
SPLITS = ("train", "dev", "test")
RAW_POOLS = ("generate.jsonl", "rewind.jsonl")   # validated teacher rows the quota filter dropped


def _norm(t: str) -> str:
    return " ".join((t or "").split()).lower()


def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(r, dict):
            out.append(r)
    return out


def positives() -> dict[str, list[dict]]:
    """Every distilled row, kept in its original split so nothing leaks across."""
    out: dict[str, list[dict]] = {}
    for split in SPLITS:
        p = SETFIT_DATA / f"{split}.jsonl"
        if not p.exists():
            raise SystemExit(f"{p} missing - run `python -m TRAINING.finetune.prepare_setfit_data` first")
        out[split] = [{"text": r["text"], "in_scope": 1, "kind": "corpus_positive",
                       "lang": r.get("lang"), "src": f"distilled:{split}"}
                      for r in _read_jsonl(p) if (r.get("text") or "").strip()]
    return out


def short_positives(max_words: int, want: int, seed: int, taken: set[str]) -> dict[str, list[dict]]:
    """Short in-scope rows pulled back from the RAW teacher output.

    The scope gate's failure mode is a length confound: the distilled corpus is 28.7 words on
    average and only 8% of it is short, while gold-180 is 11.8 words and 54% short. The gate
    then learns "short => out of scope" and rejects real field observations - the register data
    averages 9.6 words, so in production that is most of the traffic.

    These rows were already validated by the same schema as everything else; filter_distilled
    dropped them for VERDICT balance, which the scope task does not care about."""
    pool = []
    for name in RAW_POOLS:
        p = DISTILLED_RAW_DIR / name
        if not p.exists():
            continue
        for r in _read_jsonl(p):
            t = (r.get("text") or "").strip()
            k = _norm(t)
            if not t or k in taken or len(t.split()) > max_words:
                continue
            taken.add(k)
            pool.append({"text": t, "in_scope": 1, "kind": "short_positive",
                         "lang": (r.get("meta") or {}).get("lang") or r.get("lang"),
                         "src": f"raw:{name[:-6]}"})
    random.Random(seed).shuffle(pool)
    pool = pool[:want]
    n = len(pool)
    a, b = int(n * 0.70), int(n * 0.85)
    return {"train": pool[:a], "dev": pool[a:b], "test": pool[b:]}


def negatives(path: Path, seed: int) -> dict[str, list[dict]]:
    """The generated file, split 70/15/15. Mirror positives (label 1) join the positive side."""
    rows = _read_jsonl(path)
    if not rows:
        raise SystemExit(
            f"{path} is empty or missing.\n"
            "Generate it first (see TRAINING/SCOPE_GATE.md) - the gate cannot be trained\n"
            "without out-of-domain negatives; the distilled corpus has none.")
    keep, seen = [], set()
    for r in rows:
        t = (r.get("text") or "").strip()
        k = _norm(t)
        if not t or k in seen:
            continue
        seen.add(k)
        keep.append({"text": t, "in_scope": int(r.get("label", 0)),
                     "kind": r.get("kind") or ("mirror_positive" if r.get("label") else "negative"),
                     "lang": r.get("lang"), "src": f"scope:{r.get('batch', 'gen')}"})
    random.Random(seed).shuffle(keep)
    n = len(keep)
    a, b = int(n * 0.70), int(n * 0.85)
    return {"train": keep[:a], "dev": keep[a:b], "test": keep[b:]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="build the scope-gate dataset")
    ap.add_argument("--negatives", default=str(NEGATIVES))
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--max-positives", type=int, default=0,
                    help="cap positives per split (0 = keep all); use to soften the imbalance")
    ap.add_argument("--short-positives", type=int, default=1000,
                    help="short in-scope rows to pull back from the raw teacher output, to stop "
                         "the gate learning 'short = out of scope' (0 disables)")
    ap.add_argument("--short-max-words", type=int, default=14)
    a = ap.parse_args(argv)

    pos, neg = positives(), negatives(Path(a.negatives), a.seed)
    seen_pos = {_norm(r["text"]) for split in SPLITS for r in pos[split]}
    shortp = (short_positives(a.short_max_words, a.short_positives, a.seed, seen_pos)
              if a.short_positives else {s: [] for s in SPLITS})
    SCOPE_DIR.mkdir(parents=True, exist_ok=True)
    stats = {}
    for split in SPLITS:
        p = pos[split]
        if a.max_positives:
            p = random.Random(a.seed).sample(p, min(len(p), a.max_positives))
        rows = p + shortp[split] + neg[split]
        random.Random(a.seed).shuffle(rows)
        (SCOPE_DIR / f"{split}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        sw = [len(r["text"].split()) for r in rows]
        short_in = sum(1 for r in rows if r["in_scope"] == 1 and len(r["text"].split()) <= 12)
        short_out = sum(1 for r in rows if r["in_scope"] == 0 and len(r["text"].split()) <= 12)
        stats[split] = {"rows": len(rows),
                        "mean_words": round(sum(sw) / max(1, len(sw)), 1),
                        "short_le12_in_scope": short_in, "short_le12_out": short_out,
                        "pct_in_scope_among_short": round(short_in / max(1, short_in + short_out), 3),
                        "in_scope": dict(Counter(r["in_scope"] for r in rows)),
                        "kind": dict(Counter(r["kind"] for r in rows)),
                        "lang": dict(Counter(r.get("lang") for r in rows))}
        c = stats[split]["in_scope"]
        ratio = c.get(1, 0) / max(1, c.get(0, 0))
        print(f"{split:5s} {len(rows):5d} rows  in_scope={c.get(1, 0):5d} out={c.get(0, 0):4d} ({ratio:5.1f}:1)"
              f"  mean {stats[split]['mean_words']:4.1f}w"
              f"  short<=12: {short_in} in / {short_out} out"
              f"  ({stats[split]['pct_in_scope_among_short']:.0%} in-scope)")
    (SCOPE_DIR / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    long_in = sum(1 for split in SPLITS for r in (pos[split] + shortp[split])
                  if len(r["text"].split()) > 12)
    long_out = sum(1 for split in SPLITS for r in neg[split]
                   if r["in_scope"] == 0 and len(r["text"].split()) > 12)
    s_in = sum(v["short_le12_in_scope"] for v in stats.values())
    s_out = sum(v["short_le12_out"] for v in stats.values())
    a_short = s_in / max(1, s_in + s_out)
    a_long = long_in / max(1, long_in + long_out)
    print(f"\nlength confound check")
    print(f"  P(in_scope | <=12 words) = {a_short:.3f}")
    print(f"  P(in_scope |  >12 words) = {a_long:.3f}")
    gap = abs(a_short - a_long)
    print("  gap {:.3f} - {}".format(
        gap, "OK, length is no longer predictive" if gap < 0.10 else
        "STILL CONFOUNDED: raise --short-positives"))
    print(f"\n-> {SCOPE_DIR}\nnext: python -m TRAINING.finetune.train_scope --learning-curve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
