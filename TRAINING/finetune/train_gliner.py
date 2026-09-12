"""
Fine-tune GLiNER (gliner_multi-v2.1, mdeberta-v3-base backbone) on the 11 span roles.

    python -m TRAINING.finetune.train_gliner                       # auto device, 3 epochs, per-epoch checkpoints
    python -m TRAINING.finetune.train_gliner --epochs 5 --batch 8 --lr 5e-6 --resume
    python -m TRAINING.finetune.train_gliner --smoke               # 50 rows, 1 epoch - checks the loop end to end
    python -m TRAINING.finetune.train_gliner --eval-only           # span-F1 on dev/test with the saved model

Needs: pip install -r TRAINING/requirements-train.txt   (torch, gliner>=0.2.13, transformers, accelerate)
GPU strongly recommended (CPU: hours per epoch).  Checkpoints: TRAINING/checkpoints/gliner/ (HF Trainer
format, resumable with --resume).  Final model: SERVER/Classfication/Models/Tunned/gliner_sif/
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.finetune"  # noqa: A001

from ..config import BASE_MODELS_DIR, CHECKPOINT_DIR, DISTILLED_DIR, OUTPUT_MODELS_DIR  # noqa: E402
from .tokenization import install_splitter  # noqa: E402

log = logging.getLogger("train.gliner")
GLINER_DATA = DISTILLED_DIR / "gliner"
BASE_MODEL_DIR = BASE_MODELS_DIR / "gliner_multi"
BASE_MODEL_HUB = "urchade/gliner_multi-v2.1"
OUT_MODEL_DIR = OUTPUT_MODELS_DIR / "gliner_sif"
CKPT_DIR = CHECKPOINT_DIR / "gliner"


def _device(choice: str) -> str:
    import torch  # noqa: WPS433

    if choice != "auto":
        return choice
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_base(path: Path | None = None):
    from gliner import GLiNER  # noqa: WPS433

    src = str(path or (BASE_MODEL_DIR if (BASE_MODEL_DIR / "gliner_config.json").exists() else BASE_MODEL_HUB))
    log.info("loading base GLiNER from %s", src)
    try:
        model = GLiNER.from_pretrained(src)
    except Exception as exc:  # noqa: BLE001 - local dir without tokenizer files
        log.warning("local load failed (%s) - trying the hub id %s", str(exc)[:120], BASE_MODEL_HUB)
        model = GLiNER.from_pretrained(BASE_MODEL_HUB)
    install_splitter(model)
    return model


def _load_split(name: str) -> list[dict]:
    p = GLINER_DATA / f"{name}.json"
    if not p.exists():
        raise SystemExit(f"{p} missing - run `python -m TRAINING.finetune.prepare_gliner_data` first")
    data = json.loads(p.read_text(encoding="utf-8"))
    return [{"tokenized_text": d["tokenized_text"], "ner": d["ner"]} for d in data]


def evaluate(model, data: list[dict], labels: list[str], threshold: float = 0.5, batch_size: int = 12) -> dict:
    """Span-level micro P/R/F1 overall and per label (our own loop - independent of gliner's evaluate())."""
    import torch  # noqa: WPS433

    tp = {l: 0 for l in labels}
    fp = {l: 0 for l in labels}
    fn = {l: 0 for l in labels}
    model.eval()
    with torch.no_grad():
        for i in range(0, len(data), batch_size):
            chunk = data[i:i + batch_size]
            texts = [" ".join(d["tokenized_text"]) for d in chunk]
            preds = model.batch_predict_entities(texts, labels, threshold=threshold, flat_ner=False)
            for d, text, ents in zip(chunk, texts, preds):
                # gold as (start_char, end_char, label) using the joined text
                offs, pos = [], 0
                for t in d["tokenized_text"]:
                    offs.append((pos, pos + len(t)))
                    pos += len(t) + 1
                gold = {(offs[s][0], offs[e][1], l) for s, e, l in d["ner"]}
                pred = {(e["start"], e["end"], e["label"]) for e in ents}
                for g in gold:
                    (tp if g in pred else fn)[g[2]] += 1
                for p in pred - gold:
                    if p[2] in fp:
                        fp[p[2]] += 1
    def prf(t, f_p, f_n):
        p = t / (t + f_p) if t + f_p else 0.0
        r = t / (t + f_n) if t + f_n else 0.0
        return round(p, 3), round(r, 3), round(2 * p * r / (p + r), 3) if p + r else 0.0
    per = {l: dict(zip(("precision", "recall", "f1"), prf(tp[l], fp[l], fn[l]))) for l in labels}
    T, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    micro = dict(zip(("precision", "recall", "f1"), prf(T, FP, FN)))
    return {"micro": micro, "per_label": per, "n_rows": len(data), "threshold": threshold}


def _make_collator(model):
    """gliner renamed its collators across versions - resolve whichever this install has."""
    if hasattr(model, "data_collator_class"):                       # gliner >= 0.2.20
        return model.data_collator_class(model.config, data_processor=model.data_processor, prepare_labels=True)
    try:
        from gliner.data_processing.collator import DataCollator  # noqa: WPS433  (gliner <= 0.2.19)
    except ImportError:
        from gliner.data_processing.collator import SpanDataCollator as DataCollator  # noqa: WPS433
    return DataCollator(model.config, data_processor=model.data_processor, prepare_labels=True)


def train(a: argparse.Namespace) -> None:
    import torch  # noqa: WPS433
    from gliner.training import Trainer, TrainingArguments  # noqa: WPS433

    device = _device(a.device)
    labels = json.loads((GLINER_DATA / "labels.json").read_text(encoding="utf-8"))
    train_data, dev_data = _load_split("train"), _load_split("dev")
    if a.smoke:
        train_data, dev_data = train_data[:50], dev_data[:20] or train_data[:20]
        a.epochs = 1
    if not dev_data:
        dev_data = train_data[: max(1, len(train_data) // 10)]
        log.warning("no dev split - using 10%% of train for eval")
    log.info("device %s | train %d rows | dev %d rows | labels %s", device, len(train_data), len(dev_data), labels)

    model = load_base(Path(a.base) if a.base else None)
    model.to(device)
    collator = _make_collator(model)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    args = TrainingArguments(
        output_dir=str(CKPT_DIR),
        learning_rate=a.lr, weight_decay=0.01, others_lr=a.lr * 2, others_weight_decay=0.01,
        lr_scheduler_type="linear", warmup_ratio=0.1,
        per_device_train_batch_size=a.batch, per_device_eval_batch_size=a.batch,
        num_train_epochs=a.epochs,
        eval_strategy="epoch", save_strategy="epoch", save_total_limit=3, logging_steps=20,
        dataloader_num_workers=0, use_cpu=(device == "cpu"), fp16=(device == "cuda"),
        report_to="none", focal_loss_alpha=0.75, focal_loss_gamma=2,
    )
    tok = model.data_processor.transformer_tokenizer
    try:                                     # transformers >= 4.46
        trainer = Trainer(model=model, args=args, train_dataset=train_data, eval_dataset=dev_data, processing_class=tok, data_collator=collator)
    except TypeError:                        # older transformers
        trainer = Trainer(model=model, args=args, train_dataset=train_data, eval_dataset=dev_data, tokenizer=tok, data_collator=collator)
    t0 = time.time()
    resume = a.resume and any(CKPT_DIR.glob("checkpoint-*"))
    trainer.train(resume_from_checkpoint=True if resume else None)
    log.info("training finished in %.0f min", (time.time() - t0) / 60)

    OUT_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT_MODEL_DIR))
    (OUT_MODEL_DIR / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    (OUT_MODEL_DIR / "TRAINING_NOTE.txt").write_text(
        "Use TRAINING.finetune.tokenization.install_splitter(model) after loading - the model was trained with the Indic-aware word splitter.\n", encoding="utf-8")
    metrics = evaluate(model, dev_data, labels, threshold=a.threshold)
    (OUT_MODEL_DIR / "dev_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log.info("dev span-F1 micro %s | per label %s", metrics["micro"], {k: v["f1"] for k, v in metrics["per_label"].items()})
    log.info("saved -> %s", OUT_MODEL_DIR)


def eval_only(a: argparse.Namespace) -> None:
    from gliner import GLiNER  # noqa: WPS433

    model = GLiNER.from_pretrained(str(a.model or OUT_MODEL_DIR))
    install_splitter(model)
    model.to(_device(a.device))
    labels = json.loads((GLINER_DATA / "labels.json").read_text(encoding="utf-8"))
    for split in ("dev", "test"):
        p = GLINER_DATA / f"{split}.json"
        if p.exists():
            data = _load_split(split)
            if not data:
                log.warning("%s split is empty - nothing to evaluate", split)
                continue
            m = evaluate(model, data, labels, threshold=a.threshold)
            (OUT_MODEL_DIR / f"{split}_metrics.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
            print(split, json.dumps(m, indent=1))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=5e-6)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu", "mps"])
    ap.add_argument("--base", default=None, help="base model dir or hub id (default: SERVER/.../gliner_multi or urchade/gliner_multi-v2.1)")
    ap.add_argument("--model", default=None, help="eval-only: fine-tuned model dir")
    ap.add_argument("--resume", action="store_true", help="resume from the last checkpoint in TRAINING/checkpoints/gliner")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--eval-only", action="store_true")
    ap.add_argument("--clean", action="store_true", help="delete old checkpoints first")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    if a.clean and CKPT_DIR.exists():
        shutil.rmtree(CKPT_DIR)
    if a.eval_only:
        eval_only(a)
    else:
        train(a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
