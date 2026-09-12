"""
Sentence-level classifier that wraps either
  (a) a SetFit model directory (GPU-trained, full contrastive fine-tune), or
  (b) a frozen sentence-transformer + scikit-learn head(s) saved by train_setfit.py --mode head (CPU-trained)

so that evaluation and the server load both the same way:

    from TRAINING.finetune.heads import SifHeads
    heads = SifHeads.load(OUTPUT_MODELS_DIR / "sif_heads")     # SERVER/Classfication/Models/Tunned/sif_heads
    heads.predict(["LOTO nahi kiya, panel live tha"])  -> [{"prefilter": 1, "verdict": "EXPOSURE", "statement_type": "observed",
                                                             "lsr": ["Energy Isolation"], "scores": {...}}]
"""
from __future__ import annotations

import json
from pathlib import Path


class SifHeads:
    def __init__(self, encoder, heads: dict, meta: dict):
        self.encoder = encoder
        self.heads = heads          # task -> sklearn estimator (or SetFit model)
        self.meta = meta

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path) -> "SifHeads":
        path = Path(path)
        meta = json.loads((path / "heads_meta.json").read_text(encoding="utf-8"))
        if meta["mode"] == "head":
            import joblib  # noqa: WPS433
            from sentence_transformers import SentenceTransformer  # noqa: WPS433

            encoder = SentenceTransformer(meta["encoder_path"], device=meta.get("device", "cpu"))
            heads = {t: joblib.load(path / f"{t}.joblib") for t in meta["tasks"]}
            return cls(encoder, heads, meta)
        from setfit import SetFitModel  # noqa: WPS433

        heads = {t: SetFitModel.from_pretrained(str(path / t)) for t in meta["tasks"]}
        return cls(None, heads, meta)

    # ------------------------------------------------------------------
    def predict(self, texts: list[str]) -> list[dict]:
        out = [{} for _ in texts]
        if self.meta["mode"] == "head":
            X = self.encoder.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
            for task, clf in self.heads.items():
                if task == "lsr":
                    probs = clf.predict_proba(X)
                    classes = self.meta["lsr_classes"]
                    for i, row in enumerate(probs):
                        out[i]["lsr"] = [c for c, p in zip(classes, row) if p >= self.meta.get("lsr_threshold", 0.5)]
                        out[i].setdefault("scores", {})["lsr"] = {c: round(float(p), 3) for c, p in zip(classes, row)}
                else:
                    probs = clf.predict_proba(X)
                    for i, row in enumerate(probs):
                        j = int(row.argmax())
                        out[i][task] = clf.classes_[j].item() if hasattr(clf.classes_[j], "item") else clf.classes_[j]
                        out[i].setdefault("scores", {})[task] = round(float(row[j]), 3)
            return out
        for task, model in self.heads.items():
            preds = model.predict(texts)
            for i, p in enumerate(preds):
                if task == "lsr":
                    classes = self.meta["lsr_classes"]
                    out[i]["lsr"] = [c for c, flag in zip(classes, list(p)) if int(flag) == 1]
                else:
                    out[i][task] = p if not hasattr(p, "item") else p.item()
        return out
