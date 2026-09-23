from __future__ import annotations

import json
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from SERVER.DB.models import thresholds, verdicts, actions

# Model directories (match INFERENCE/config.py)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODELS_DIR = _REPO_ROOT / "SERVER" / "Classfication" / "Models"
_TUNED = _MODELS_DIR / "Tunned"
_RAW = _MODELS_DIR / "RAW"


def _check_model_dir(path: Path) -> bool:
    """True if the directory exists and has at least one model file."""
    if not path.is_dir():
        return False
    exts = {".safetensors", ".bin", ".joblib", ".gguf", ".onnx", ".pt"}
    return any(f.suffix in exts for f in path.rglob("*"))


def get_health(session: Connection) -> dict:
    # Check DB connectivity
    try:
        session.execute(sa.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # Check models
    gliner_ok = _check_model_dir(_TUNED / "gliner_sif") or _check_model_dir(_RAW / "gliner_multi")
    heads_ok = _check_model_dir(_TUNED / "sif_heads")
    scope_ok = (_TUNED / "scope_gate" / "scope.joblib").exists()
    encoder_ok = _check_model_dir(_RAW / "sentance_encoder")

    models_loaded = gliner_ok and heads_ok and encoder_ok

    # Queue depth
    queue_depth = 0
    if db_ok:
        try:
            q = sa.select(sa.func.count()).select_from(
                verdicts.outerjoin(actions, verdicts.c.verdict_id == actions.c.verdict_id)
            ).where(
                verdicts.c.review_required == True,
                verdicts.c.is_current == True,
                actions.c.action_id == None
            )
            queue_depth = session.execute(q).scalar() or 0
        except Exception:
            pass

    return {
        "status": "ok" if db_ok else "degraded",
        "db_connected": db_ok,
        "models_loaded": models_loaded,
        "pipeline_version": "0.7.0",
        "queue_depth": queue_depth,
        "layers": {
            "rules": True,
            "gliner": gliner_ok,
            "heads": heads_ok,
            "scope_gate": scope_ok,
            "encoder": encoder_ok,
        }
    }


def get_models() -> list[dict]:
    models = []

    # GLiNER
    tuned_gliner = _TUNED / "gliner_sif"
    base_gliner = _RAW / "gliner_multi"
    gliner_loaded = _check_model_dir(tuned_gliner)
    models.append({
        "name": "GLiNER SIF (Span Extraction)",
        "model_type": "gliner",
        "loaded": gliner_loaded,
        "version": "tuned" if gliner_loaded else ("base" if _check_model_dir(base_gliner) else None),
        "path": str(tuned_gliner) if gliner_loaded else str(base_gliner),
        "last_finetune": None,
    })

    # SetFit Heads
    heads_dir = _TUNED / "sif_heads"
    heads_loaded = _check_model_dir(heads_dir)
    head_names = [f.stem for f in heads_dir.glob("*.joblib")] if heads_dir.is_dir() else []
    meta_path = heads_dir / "heads_meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    models.append({
        "name": "SetFit Classification Heads",
        "model_type": "setfit_heads",
        "loaded": heads_loaded,
        "version": f"{len(head_names)} heads: {', '.join(head_names)}" if head_names else None,
        "last_finetune": meta.get("trained_at"),
    })

    # Scope Gate
    scope_path = _TUNED / "scope_gate" / "scope.joblib"
    scope_loaded = scope_path.exists()
    scope_meta_path = _TUNED / "scope_gate" / "scope_meta.json"
    scope_meta = {}
    if scope_meta_path.exists():
        try:
            scope_meta = json.loads(scope_meta_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    models.append({
        "name": "Scope Gate (Pre-filter)",
        "model_type": "scope_gate",
        "loaded": scope_loaded,
        "version": f"threshold={scope_meta.get('threshold', 0.90)}" if scope_loaded else None,
        "last_finetune": scope_meta.get("trained_at"),
    })

    # Sentence Encoder
    encoder_dir = _RAW / "sentance_encoder"
    encoder_loaded = _check_model_dir(encoder_dir)
    models.append({
        "name": "Sentence Encoder (Multilingual)",
        "model_type": "sentence_transformer",
        "loaded": encoder_loaded,
        "version": "base",
        "last_finetune": None,
    })

    # LLM (Qwen GGUF)
    llm_dir = _MODELS_DIR / "LLM"
    llm_files = list(llm_dir.glob("*.gguf")) if llm_dir.is_dir() else []
    llm_loaded = len(llm_files) > 0
    models.append({
        "name": llm_files[0].name if llm_loaded else "Qwen LLM (GGUF)",
        "model_type": "llm_gguf",
        "loaded": llm_loaded,
        "version": f"{llm_files[0].stat().st_size / (1024**3):.1f} GB" if llm_loaded else None,
        "last_finetune": None,
    })

    return models


def get_config(session: Connection) -> dict:
    stmt = sa.select(thresholds)
    results = [dict(r) for r in session.execute(stmt).mappings()]
    return {
        "thresholds": results,
        "pipeline_version": "0.7.0",
        "scope_enabled": True,
        "review_confidence_cutoff": 0.55,
    }


def get_sync_status() -> dict:
    return {"status": "standalone", "last_sync": None, "pending_rows": 0, "mode": "hub"}
