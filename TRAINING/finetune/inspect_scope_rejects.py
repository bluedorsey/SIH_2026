"""
Which gold rows does the scope gate reject, and WHICH TRAINING NEGATIVE taught it to?

    python -m TRAINING.finetune.inspect_scope_rejects
    python -m TRAINING.finetune.inspect_scope_rejects --threshold 0.90 --top 3

For every gold row above the threshold it prints p_out and the nearest negatives in the
training set by cosine similarity. A rejected precursor sitting next to a hard_negative of the
same surface form ("<room> ka <equipment> kharab hai") names the poisoned pattern directly -
that negative has to be reclassified, and its hazard twin added as a mirror positive.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.finetune"  # noqa: A001

from ..config import DATA_DIR, GOLD_JSONL, OUTPUT_MODELS_DIR  # noqa: E402
from .train_scope import encoder_path  # noqa: E402

OUT_DIR = OUTPUT_MODELS_DIR / "scope_gate"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="explain the scope gate's gold rejections")
    ap.add_argument("--threshold", type=float, default=None, help="default: the shipped one")
    ap.add_argument("--top", type=int, default=3, help="nearest negatives to show per row")
    ap.add_argument("--limit", type=int, default=25)
    a = ap.parse_args(argv)

    import joblib  # noqa: WPS433
    import numpy as np  # noqa: WPS433
    from sentence_transformers import SentenceTransformer  # noqa: WPS433

    clf = joblib.load(OUT_DIR / "scope.joblib")
    meta = json.loads((OUT_DIR / "scope_meta.json").read_text(encoding="utf-8"))
    thr = a.threshold if a.threshold is not None else float(meta.get("threshold", 0.9))
    enc = SentenceTransformer(encoder_path(meta.get("encoder_path")), device="cpu")

    gold = [json.loads(l) for l in GOLD_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = [g for g in gold if (g.get("text") or "").strip()]
    train = [json.loads(l) for l in (DATA_DIR / "scope" / "train.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    negs = [r for r in train if r["in_scope"] == 0]

    Xg = enc.encode([g["text"] for g in gold], batch_size=64, normalize_embeddings=True)
    Xn = enc.encode([r["text"] for r in negs], batch_size=64, normalize_embeddings=True)
    col = list(clf.classes_).index(0)
    p = np.asarray(clf.predict_proba(Xg))[:, col]

    # ---- confound check: is the gate scoring LENGTH instead of topic? ---------------------
    lens = np.array([len(g["text"].split()) for g in gold], dtype=float)
    r = float(np.corrcoef(lens, p)[0, 1])
    tr_len = np.array([len(x["text"].split()) for x in train], dtype=float)
    tr_y = np.array([x["in_scope"] for x in train], dtype=float)
    print(f"length confound")
    print(f"  corr(word_count, p_out) on gold : {r:+.3f}   "
          f"{'<- STRONG: the gate is scoring length, not topic' if r < -0.35 else ''}")
    print(f"  mean words  in-scope train       : {tr_len[tr_y == 1].mean():5.1f}")
    print(f"  mean words  out-of-scope train   : {tr_len[tr_y == 0].mean():5.1f}")
    print(f"  mean words  gold                 : {lens.mean():5.1f}")
    short, long_ = lens <= 12, lens > 12
    if short.any() and long_.any():
        print(f"  mean p_out  gold <=12 words      : {p[short].mean():.3f}")
        print(f"  mean p_out  gold  >12 words      : {p[long_].mean():.3f}")
    print()

    order = np.argsort(-p)
    hits = [i for i in order if p[i] > thr][:a.limit]
    print(f"threshold {thr}  -  {len(hits)} gold row(s) rejected of {len(gold)}\n")
    for i in hits:
        sims = np.asarray(Xn) @ np.asarray(Xg[i])
        near = np.argsort(-sims)[:a.top]
        gid = gold[i].get("gold_id") or gold[i].get("id") or f"row{i}"
        print(f"p_out={p[i]:.4f}  [{gid}]  {gold[i]['text'][:110]}")
        for j in near:
            print(f"        sim {sims[j]:.3f}  ({negs[j].get('kind', '?')})  {negs[j]['text'][:96]}")
        print()
    if not hits:
        print("nothing rejected at this threshold.")
    print("Any rejected precursor whose nearest neighbour is a hard_negative of the same shape\n"
          "is a poisoned pattern: reclassify that negative and add its hazard twin as a\n"
          "mirror_positive, then retrain. That is worth far more than another 300 rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
