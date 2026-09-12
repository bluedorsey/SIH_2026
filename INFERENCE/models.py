"""Lazy, fault-tolerant wrappers around the tuned models.

Nothing here raises if a model folder is missing: `available` goes False and the pipeline runs on
the layers it does have. That is what lets the service start before fine-tuning is finished.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .config import ENCODER_DIR, GLINER_BASE, GLINER_TUNED, HEADS_DIR, SPAN_ROLES, SPAN_THRESHOLD

log = logging.getLogger("inference.models")

# GLiNER is prompted with natural-language labels; map them back to our role vocabulary
ROLE_PROMPTS = {
    "energy source": "energy_cue",
    "energy released": "release_cue",
    "not released yet": "no_release_cue",
    "person exposed": "exposure_cue",
    "control present": "control_present",
    "control absent": "control_absent",
    "control ineffective": "control_ineffective",
    "pseudo control": "pseudo_control",
    "negation word": "negation_cue",
    "outcome": "outcome_cue",
    "statement marker": "statement_cue",
}


class SpanExtractor:
    """GLiNER. Prefers the tuned model, falls back to the base one (zero-shot, weaker)."""

    def __init__(self) -> None:
        self.model = None
        self.source: str | None = None
        self.available = False

    def load(self) -> "SpanExtractor":
        if self.model is not None:
            return self
        for path, tag in ((GLINER_TUNED, "gliner_sif"), (GLINER_BASE, "gliner_multi")):
            if not Path(path).is_dir():
                continue
            try:
                from gliner import GLiNER  # noqa: WPS433
                self.model = GLiNER.from_pretrained(str(path))
                self.model.eval()
                try:                                    # Indic-aware splitter used during training
                    from TRAINING.finetune.tokenization import install_splitter  # noqa: WPS433
                    install_splitter(self.model)
                except Exception:                       # noqa: BLE001  (production must not need TRAINING)
                    pass
                self.source, self.available = tag, True
                log.info("GLiNER loaded from %s", path)
                return self
            except Exception as exc:                    # noqa: BLE001
                log.warning("GLiNER not loadable from %s: %s", path, str(exc)[:160])
        log.warning("no GLiNER available - running on rules only")
        return self

    def spans(self, text: str) -> list[dict]:
        if not self.available:
            return []
        try:
            ents = self.model.predict_entities(text, list(ROLE_PROMPTS), threshold=SPAN_THRESHOLD)
        except Exception as exc:                        # noqa: BLE001
            log.warning("GLiNER inference failed: %s", str(exc)[:160])
            return []
        out = []
        for e in ents:
            role = ROLE_PROMPTS.get(e["label"], e["label"])
            if role not in SPAN_ROLES:
                continue
            out.append({"role": role, "text": e["text"], "start": e["start"], "end": e["end"],
                        "score": round(float(e.get("score", 0.0)), 4), "source": "gliner"})
        return out


class Heads:
    """SetFit sentence heads: prefilter / verdict / statement_type / LSR."""

    def __init__(self) -> None:
        self.bundle = None
        self.available = False
        self.names: list[str] = []

    def load(self) -> "Heads":
        if self.bundle is not None:
            return self
        if not Path(HEADS_DIR).is_dir():
            log.warning("no tuned heads at %s - the verdict comes from the rules tree", HEADS_DIR)
            return self
        try:
            import joblib  # noqa: WPS433
            from sentence_transformers import SentenceTransformer  # noqa: WPS433

            heads = {f.stem: joblib.load(f) for f in sorted(Path(HEADS_DIR).glob("*.joblib"))}
            if not heads:
                log.warning("%s has no *.joblib heads", HEADS_DIR)
                return self
            encoder = SentenceTransformer(str(ENCODER_DIR), device="cpu")
            self.bundle = {"encoder": encoder, "heads": heads}
            self.names = sorted(heads)
            self.available = True
            log.info("heads loaded: %s", ", ".join(self.names))
        except Exception as exc:                        # noqa: BLE001
            log.warning("heads not loadable: %s", str(exc)[:160])
        return self

    def predict(self, text: str) -> dict:
        if not self.available:
            return {}
        try:
            vec = self.bundle["encoder"].encode([text], normalize_embeddings=True)
        except Exception as exc:                        # noqa: BLE001
            log.warning("encoder failed: %s", str(exc)[:160])
            return {}
        out = {}
        for name, clf in self.bundle["heads"].items():
            try:
                if hasattr(clf, "predict_proba"):
                    p = clf.predict_proba(vec)[0]
                    i = int(p.argmax())
                    out[name] = {"label": str(clf.classes_[i]), "confidence": round(float(p[i]), 4),
                                 "proba": {str(c): round(float(v), 4) for c, v in zip(clf.classes_, p)}}
                else:
                    out[name] = {"label": str(clf.predict(vec)[0]), "confidence": None, "proba": {}}
            except Exception as exc:                    # noqa: BLE001
                log.warning("head %s failed: %s", name, str(exc)[:120])
        return out


_EXTRACTOR: SpanExtractor | None = None
_HEADS: Heads | None = None


def get_extractor() -> SpanExtractor:
    global _EXTRACTOR                                   # noqa: PLW0603
    if _EXTRACTOR is None:
        _EXTRACTOR = SpanExtractor().load()
    return _EXTRACTOR


def get_heads() -> Heads:
    global _HEADS                                       # noqa: PLW0603
    if _HEADS is None:
        _HEADS = Heads().load()
    return _HEADS
