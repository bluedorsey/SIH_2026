"""
Train the scope gate: frozen multilingual encoder -> one logistic layer.

    python -m TRAINING.finetune.train_scope
    python -m TRAINING.finetune.train_scope --C 1.0 --min-threshold 0.80
    python -m TRAINING.finetune.train_scope --no-gold-sweep     # skip the gold-180 acceptance bar

The encoder is NEVER fine-tuned. 118M encoder params on a few hundred negatives is how the
SetFit body run reached train loss 0.002 against eval 0.281. The head here is 385 parameters
(384 dims + bias) and cannot memorise its way out of the task.

THRESHOLD SELECTION is part of training, not an afterthought. The operating point is the
LOWEST P(out_of_scope) cut that rejects ZERO rows of gold-180 (at or above --min-threshold).
Lowest, because among the safe cuts the lowest one catches the most junk. One rejected gold
row is one dead precursor, so the bar is a count of 0 - not 99%, not "close".

Output: SERVER/Classfication/Models/Tunned/scope_gate/{scope.joblib,scope_meta.json}
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.finetune"  # noqa: A001

from ..config import BASE_MODELS_DIR, DATA_DIR, GOLD_JSONL, OUTPUT_MODELS_DIR  # noqa: E402

log = logging.getLogger("train.scope")
SCOPE_DATA = DATA_DIR / "scope"
ENCODER_LOCAL = BASE_MODELS_DIR / "sentance_encoder"
ENCODER_HUB = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OUT_DIR = OUTPUT_MODELS_DIR / "scope_gate"
SWEEP = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.93, 0.95, 0.97, 0.99]


def encoder_path(override: str | None = None) -> str:
    if override:
        return override
    if (ENCODER_LOCAL / "modules.json").exists() and (ENCODER_LOCAL / "config.json").exists():
        return str(ENCODER_LOCAL)
    log.warning("%s incomplete - falling back to hub id %s", ENCODER_LOCAL, ENCODER_HUB)
    return ENCODER_HUB


def _load(split: str) -> list[dict]:
    p = SCOPE_DATA / f"{split}.jsonl"
    if not p.exists():
        raise SystemExit(f"{p} missing - run `python -m TRAINING.finetune.prepare_scope_data`")
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _gold_rows() -> list[tuple[str, str]]:
    """(text, sif_potential) for every gold row.

    The acceptance bar counts rejections of sif_potential == YES ONLY. gold-180 is half NO and
    UNCERTAIN - administrative notes, requests, minor ergonomic injuries - and rejecting those
    is not "a dead precursor", it is often the gate being right. Counting all 180 as precursors
    is what kept forcing the threshold to 0.99 where the gate does nothing."""
    if not GOLD_JSONL.exists():
        log.warning("gold set not found at %s - acceptance bar skipped", GOLD_JSONL)
        return []
    out = []
    for ln in GOLD_JSONL.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        r = json.loads(ln)
        if (r.get("text") or "").strip():
            out.append((r["text"].strip(), str(r.get("sif_potential") or "UNCERTAIN").upper()))
    return out


def _p_out(clf, X):
    """P(out_of_scope) for each row, whichever way sklearn ordered the classes."""
    import numpy as np  # noqa: WPS433
    proba = clf.predict_proba(X)
    col = list(clf.classes_).index(0)
    return np.asarray(proba)[:, col]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="train the scope gate (frozen encoder + logistic head)")
    ap.add_argument("--encoder", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--C", type=float, default=1.0, help="inverse regularisation (lower = stronger)")
    ap.add_argument("--min-threshold", type=float, default=0.70,
                    help="never ship an operating point below this")
    ap.add_argument("--no-gold-sweep", action="store_true")
    ap.add_argument("--min-dev-negatives", type=int, default=30,
                    help="below this the dev metrics and the learning curve cannot resolve "
                         "anything; the gate is saved but shipped DISABLED")
    ap.add_argument("--min-train-negatives", type=int, default=150,
                    help="below this the decision boundary is drawn through noise")
    ap.add_argument("--learning-curve", action="store_true",
                    help="retrain at 25/50/75/100%% of the NEGATIVES and print dev recall at each "
                         "point. A flat tail means more negatives will not help and the problem is "
                         "elsewhere; a rising tail means keep collecting.")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING,
                        format="%(levelname)-7s %(name)s: %(message)s")

    import joblib  # noqa: WPS433
    from sentence_transformers import SentenceTransformer  # noqa: WPS433
    from sklearn.linear_model import LogisticRegression  # noqa: WPS433
    from sklearn.metrics import precision_score, recall_score  # noqa: WPS433

    train, dev = _load("train"), _load("dev")
    if len({r["in_scope"] for r in train}) < 2:
        raise SystemExit("train split has a single class - add negatives to DATA/scope/negatives.jsonl")

    enc_path = encoder_path(a.encoder)
    enc = SentenceTransformer(enc_path, device=a.device)
    t0 = time.time()
    Xtr = enc.encode([r["text"] for r in train], batch_size=64, normalize_embeddings=True, show_progress_bar=True)
    Xdv = enc.encode([r["text"] for r in dev], batch_size=64, normalize_embeddings=True)
    ytr = [r["in_scope"] for r in train]
    ydv = [r["in_scope"] for r in dev]
    print(f"encoded {len(train)} + {len(dev)} texts in {time.time() - t0:.0f}s")

    n_neg_tr = len(ytr) - sum(ytr)
    n_neg_dv = len(ydv) - sum(ydv)
    starved = []
    if n_neg_tr < a.min_train_negatives:
        starved.append(f"train has {n_neg_tr} negatives (need >= {a.min_train_negatives}): "
                       f"a 384-dim boundary fitted on this few points is drawn through noise")
    if n_neg_dv < a.min_dev_negatives:
        starved.append(f"dev has {n_neg_dv} negatives (need >= {a.min_dev_negatives}): "
                       f"every out-of-scope metric below is statistically meaningless")
    if starved:
        print("\n!! DATA STARVED - this gate will NOT be enabled:")
        for s in starved:
            print("   * " + s)
        print("   Generate more negatives and retrain. Nothing here is a result yet.\n")

    clf = LogisticRegression(max_iter=3000, class_weight="balanced", C=a.C)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xdv)
    dev_metrics = {
        # the number that matters: of genuine safety rows, how many survive the gate
        "recall_in_scope": round(recall_score(ydv, pred, pos_label=1, zero_division=0), 4),
        "precision_in_scope": round(precision_score(ydv, pred, pos_label=1, zero_division=0), 4),
        "recall_out_of_scope": round(recall_score(ydv, pred, pos_label=0, zero_division=0), 4),
        "accuracy": round(sum(int(x == y) for x, y in zip(ydv, pred)) / max(1, len(ydv)), 4),
        "dev_rows": len(dev),
    }
    print("\ndev (argmax):", json.dumps(dev_metrics, indent=2))

    if a.learning_curve and n_neg_dv < a.min_dev_negatives:
        print(f"\nlearning curve SKIPPED - {n_neg_dv} dev negatives cannot resolve a difference. "
              f"It would print numbers that mean nothing.")
    elif a.learning_curve:
        import numpy as np  # noqa: WPS433
        neg_i = [i for i, y in enumerate(ytr) if y == 0]
        pos_i = [i for i, y in enumerate(ytr) if y == 1]
        rng = __import__("random").Random(7)
        rng.shuffle(neg_i)
        print("\nlearning curve - does adding negatives still buy anything?")
        print(f"{'negatives':>10} {'out-recall':>11} {'in-recall':>10} {'accuracy':>9}")
        for frac in (0.25, 0.50, 0.75, 1.0):
            k = max(2, int(len(neg_i) * frac))
            idx = pos_i + neg_i[:k]
            c = LogisticRegression(max_iter=3000, class_weight="balanced", C=a.C)
            c.fit(np.asarray(Xtr)[idx], [ytr[i] for i in idx])
            pr = c.predict(Xdv)
            print(f"{k:10d} "
                  f"{recall_score(ydv, pr, pos_label=0, zero_division=0):11.3f} "
                  f"{recall_score(ydv, pr, pos_label=1, zero_division=0):10.3f} "
                  f"{sum(int(x == y) for x, y in zip(ydv, pr)) / max(1, len(ydv)):9.3f}")
        print("flat tail -> stop collecting; rising tail -> keep going")

    # ---- acceptance bar: the highest cut that rejects nothing in gold-180 -------------------
    gold_rows = [] if a.no_gold_sweep else _gold_rows()
    gold = [t for t, _ in gold_rows]
    is_yes = [lbl == "YES" for _, lbl in gold_rows]
    n_yes = sum(is_yes)
    sweep, chosen = [], None
    if gold:
        pg = _p_out(clf, enc.encode(gold, batch_size=64, normalize_embeddings=True))
        pd_ = _p_out(clf, Xdv)
        out_dev = [i for i, y in enumerate(ydv) if y == 0]
        print(f"\nthreshold sweep - {n_yes} SIF precursors (sif=YES) of {len(gold)} gold rows, "
              f"{len(out_dev)} dev negatives")
        print(f"{'thr':>6} {'PRECURSORS lost':>16} {'other gold':>11} {'junk caught':>13}")
        for thr in SWEEP:
            above = pg > thr
            lost = int(sum(1 for i, y in enumerate(is_yes) if y and above[i]))
            other = int(above.sum()) - lost
            caught = sum(1 for i in out_dev if pd_[i] > thr)
            rate = caught / max(1, len(out_dev))
            sweep.append({"threshold": thr, "precursors_lost": lost, "other_gold_rejected": other,
                          "gold_rejected": int(above.sum()),
                          "junk_caught": caught, "junk_rate": round(rate, 3)})
            flag = "  <- FAILS (drops precursors)" if lost else ""
            print(f"{thr:6.2f} {lost:16d} {other:11d} {caught:7d} ({rate:4.0%}){flag}")
            if lost == 0 and thr >= a.min_threshold and chosen is None:
                chosen = thr           # lowest safe cut at/above the floor = most junk caught
        if chosen is not None:
            at = next(s for s in sweep if s["threshold"] == chosen)
            if at["junk_caught"] == 0:
                print(f"\n!! threshold {chosen} clears the gold bar only by rejecting NOTHING "
                      f"({at['junk_caught']}/{len(out_dev)} junk caught). "
                      f"That is an inert gate, not a safe one.")
                starved.append(f"operating point {chosen} catches 0 out-of-scope rows - inert")
        if chosen is None:
            print("\n!! no threshold clears the bar: the gate drops a sif=YES precursor even at 0.99.")
            print("   Shipping DISABLED (scope_enabled=false). Add negatives / mirror positives and retrain.")
    else:
        print("\n(no gold sweep - the shipped threshold is the config default)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, OUT_DIR / "scope.joblib")
    meta = {
        "mode": "frozen_encoder+logistic",
        "encoder_path": enc_path,
        "classes": [int(c) for c in clf.classes_],
        "positive_label": 1,
        "threshold": chosen if chosen is not None else 0.99,
        "scope_enabled": bool((chosen is not None or not gold) and not starved),
        "starved": starved,
        "min_threshold": a.min_threshold,
        "C": a.C,
        "train_rows": len(train),
        "train_class_counts": {"in_scope": sum(ytr), "out_of_scope": len(ytr) - sum(ytr)},
        "dev_metrics": dev_metrics,
        "gold_sweep": sweep,
        "gold_rows": len(gold),
        "gold_precursors": n_yes,
        "acceptance_bar": "0 rows with sif_potential==YES rejected",
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / "scope_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\nsaved -> {OUT_DIR}")
    print(f"operating point: threshold={meta['threshold']}  enabled={meta['scope_enabled']}")
    print("next: python -m INFERENCE.evaluate_scope --probe DATA/scope/probe.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
