"""
Train the sentence-level heads (prefilter / verdict / statement_type / LSR) on multilingual MiniLM.

Two modes - same output layout (loadable with TRAINING.finetune.heads.SifHeads):

  --mode head   (CPU, minutes)   frozen encoder -> embeddings once -> scikit-learn logistic-regression heads
                                 (class_weight balanced; LSR = one-vs-rest).  Fast iteration, ablations, laptop.
  --mode setfit (GPU, ~30 min)   full SetFit contrastive fine-tune of the encoder per task, per-epoch checkpoints.

    python -m TRAINING.finetune.train_setfit --mode head
    python -m TRAINING.finetune.train_setfit --mode setfit --tasks prefilter,statement_type --epochs 1 --iterations 10
    python -m TRAINING.finetune.train_setfit --mode head --smoke

Encoder: SERVER/Classfication/Models/sentance_encoder if it is a complete sentence-transformers folder,
else `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` from the hub (run TRAINING.setup_models first).
Output: SERVER/Classfication/Models/Tunned/sif_heads/  (+ dev metrics)
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

from ..config import BASE_MODELS_DIR, CHECKPOINT_DIR, DISTILLED_DIR, LSR_NAMES, OUTPUT_MODELS_DIR, STATEMENT_TYPES, VERDICTS  # noqa: E402

log = logging.getLogger("train.setfit")
SETFIT_DATA = DISTILLED_DIR / "setfit"
ENCODER_LOCAL = BASE_MODELS_DIR / "sentance_encoder"
ENCODER_HUB = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OUT_DIR = OUTPUT_MODELS_DIR / "sif_heads"
TASKS = ["prefilter", "verdict", "statement_type", "lsr"]


def encoder_path(override: str | None = None) -> str:
    if override:
        return override
    if (ENCODER_LOCAL / "modules.json").exists() and (ENCODER_LOCAL / "config.json").exists():
        return str(ENCODER_LOCAL)
    log.warning("%s is not a complete sentence-transformers folder - using hub id %s (run TRAINING.setup_models to fix)", ENCODER_LOCAL, ENCODER_HUB)
    return ENCODER_HUB


def _load(split: str) -> list[dict]:
    p = SETFIT_DATA / f"{split}.jsonl"
    if not p.exists():
        raise SystemExit(f"{p} missing - run `python -m TRAINING.finetune.prepare_setfit_data`")
    return [json.loads(ln) for ln in open(p, "r", encoding="utf-8") if ln.strip()]


def _labels(rows: list[dict], task: str):
    if task == "lsr":
        return [[1 if l in r["lsr"] else 0 for l in LSR_NAMES] for r in rows]
    return [r[task] for r in rows]


def _metrics(task: str, y_true, y_pred) -> dict:
    from sklearn.metrics import f1_score, fbeta_score, precision_score, recall_score  # noqa: WPS433

    if task == "lsr":
        return {"micro_f1": round(f1_score(y_true, y_pred, average="micro", zero_division=0), 3),
                "macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 3)}
    m = {"macro_f1": round(f1_score(y_true, y_pred, average="macro", zero_division=0), 3),
         "accuracy": round(sum(int(a == b) for a, b in zip(y_true, y_pred)) / max(1, len(y_true)), 3)}
    if task == "prefilter":
        m.update({"recall_sif": round(recall_score(y_true, y_pred, pos_label=1, zero_division=0), 3),
                  "precision_sif": round(precision_score(y_true, y_pred, pos_label=1, zero_division=0), 3),
                  "f2_sif": round(fbeta_score(y_true, y_pred, beta=2, pos_label=1, zero_division=0), 3)})
    return m


# --------------------------------------------------------------------------
# mode: head (CPU)
# --------------------------------------------------------------------------
def train_head(a: argparse.Namespace, tasks: list[str]) -> None:
    import joblib  # noqa: WPS433
    import numpy as np  # noqa: WPS433
    from sentence_transformers import SentenceTransformer  # noqa: WPS433
    from sklearn.linear_model import LogisticRegression  # noqa: WPS433
    from sklearn.multiclass import OneVsRestClassifier  # noqa: WPS433

    train, dev = _load("train"), _load("dev")
    if a.smoke:
        train, dev = train[:200], dev[:50] or train[:50]
    if not dev:
        dev = train[: max(1, len(train) // 10)]
    enc_path = encoder_path(a.encoder)
    enc = SentenceTransformer(enc_path, device=a.device if a.device != "auto" else None)
    t0 = time.time()
    Xtr = enc.encode([r["text"] for r in train], batch_size=64, normalize_embeddings=True, show_progress_bar=True)
    Xdv = enc.encode([r["text"] for r in dev], batch_size=64, normalize_embeddings=True, show_progress_bar=False)
    log.info("encoded %d + %d texts in %.0fs", len(train), len(dev), time.time() - t0)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for task in tasks:
        ytr, ydv = _labels(train, task), _labels(dev, task)
        if task == "lsr":
            clf = OneVsRestClassifier(LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0))
            clf.fit(Xtr, np.array(ytr))
            pred = clf.predict(Xdv)
        else:
            if len(set(ytr)) < 2:
                log.warning("task %s has a single class in train - skipped", task)
                continue
            clf = LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0)
            clf.fit(Xtr, ytr)
            pred = clf.predict(Xdv)
        joblib.dump(clf, OUT_DIR / f"{task}.joblib")
        metrics[task] = _metrics(task, ydv, pred)
        log.info("%s: %s", task, metrics[task])
    meta = {"mode": "head", "encoder_path": enc_path, "tasks": [t for t in tasks if (OUT_DIR / f"{t}.joblib").exists()],
            "lsr_classes": LSR_NAMES, "lsr_threshold": 0.5, "verdict_classes": VERDICTS, "statement_classes": STATEMENT_TYPES,
            "device": "cpu", "train_rows": len(train), "dev_metrics": metrics}
    (OUT_DIR / "heads_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("saved -> %s", OUT_DIR)


# --------------------------------------------------------------------------
# mode: setfit (GPU)
# --------------------------------------------------------------------------
def train_setfit(a: argparse.Namespace, tasks: list[str]) -> None:
    from datasets import Dataset  # noqa: WPS433
    from setfit import SetFitModel, Trainer, TrainingArguments  # noqa: WPS433

    train, dev = _load("train"), _load("dev")
    if a.smoke:
        train, dev = train[:200], dev[:50] or train[:50]
    if not dev:
        dev = train[: max(1, len(train) // 10)]
    enc_path = encoder_path(a.encoder)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {}
    for task in tasks:
        ytr, ydv = _labels(train, task), _labels(dev, task)
        ds_tr = Dataset.from_list([{"text": r["text"], "label": y} for r, y in zip(train, ytr)])
        ds_dv = Dataset.from_list([{"text": r["text"], "label": y} for r, y in zip(dev, ydv)])
        kw = {"multi_target_strategy": "one-vs-rest"} if task == "lsr" else {}
        model = SetFitModel.from_pretrained(enc_path, **kw)
        ckpt = CHECKPOINT_DIR / "setfit" / task
        ckpt.mkdir(parents=True, exist_ok=True)
        args = TrainingArguments(output_dir=str(ckpt), batch_size=a.batch, num_epochs=a.epochs, num_iterations=a.iterations,
                                 eval_strategy="epoch", save_strategy="epoch", save_total_limit=2, logging_steps=50,
                                 sampling_strategy="oversampling" if task != "lsr" else "unique", report_to="none")
        trainer = Trainer(model=model, args=args, train_dataset=ds_tr, eval_dataset=ds_dv, metric="f1" if task != "lsr" else None,
                          column_mapping={"text": "text", "label": "label"})
        t0 = time.time()
        trainer.train()
        log.info("%s trained in %.0f min", task, (time.time() - t0) / 60)
        pred = model.predict([r["text"] for r in dev])
        pred = [list(map(int, p)) for p in pred] if task == "lsr" else [p.item() if hasattr(p, "item") else p for p in pred]
        metrics[task] = _metrics(task, ydv, pred)
        log.info("%s: %s", task, metrics[task])
        model.save_pretrained(str(OUT_DIR / task))
    meta = {"mode": "setfit", "encoder_path": enc_path, "tasks": tasks, "lsr_classes": LSR_NAMES,
            "verdict_classes": VERDICTS, "statement_classes": STATEMENT_TYPES, "train_rows": len(train), "dev_metrics": metrics}
    (OUT_DIR / "heads_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log.info("saved -> %s", OUT_DIR)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["head", "setfit"], default="head")
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--iterations", type=int, default=20, help="setfit: contrastive pair iterations per sample")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--encoder", default=None, help="sentence-transformers dir or hub id (default: Models/sentance_encoder or multilingual MiniLM)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    tasks = [t for t in a.tasks.split(",") if t in TASKS]
    (train_head if a.mode == "head" else train_setfit)(a, tasks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
