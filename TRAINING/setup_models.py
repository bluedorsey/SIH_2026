"""
Repair / complete the base-model folders under SERVER/Classfication/Models/RAW and verify they load.

    python -m TRAINING.setup_models            # download what is missing, then verify
    python -m TRAINING.setup_models --verify   # only check
    python -m TRAINING.setup_models --encoder intfloat/multilingual-e5-small   # alternative encoder

What it fixes (found 2026-09-06):
  sentance_encoder/  only openvino/*.bin + tf_model.h5 -> no config.json / tokenizer / modules.json -> unloadable
  bert/              mDeBERTa NLI weights + tokenizer but no config.json -> unloadable
  gliner_multi/      OK (gliner_config.json + model.safetensors) but the mdeberta tokenizer is fetched from the hub
                     on first load -> we snapshot it next to the model so the box can run offline
Needs internet once. Requires: pip install -r TRAINING/requirements-train.txt
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "TRAINING"  # noqa: A001

from .config import BASE_MODELS_DIR, MODELS_DIR  # noqa: E402

log = logging.getLogger("setup_models")
ENCODER_DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
NLI_DEFAULT = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
GLINER_HUB = "urchade/gliner_multi-v2.1"
GLINER_BACKBONE = "microsoft/mdeberta-v3-base"


# pytorch_model.bin is the same weights as model.safetensors - skipping it halves the download
# and avoids the 470 MB transfer that most often breaks on a flaky connection.
_IGNORE = ["*.onnx", "openvino/*", "*.h5", "*.msgpack", "rust_model.ot", "pytorch_model.bin", "*.ot"]


def _snapshot(repo: str, dest: Path, allow: list[str] | None = None, tries: int = 4) -> Path:
    from huggingface_hub import snapshot_download  # noqa: WPS433

    dest.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s -> %s", repo, dest)
    last = None
    for attempt in range(1, tries + 1):
        try:
            snapshot_download(repo_id=repo, local_dir=str(dest), allow_patterns=allow,
                              ignore_patterns=_IGNORE, max_workers=2)
            return dest
        except Exception as exc:  # noqa: BLE001  (network drops mid-file: resume and retry)
            last = exc
            log.warning("download attempt %d/%d failed (%s) - resuming", attempt, tries, str(exc)[:120])
            time.sleep(5 * attempt)
    raise SystemExit(f"could not download {repo} after {tries} attempts: {str(last)[:200]}\n"
                     f"Re-run `python -m TRAINING.setup_models` - finished files are kept and resumed.")


def fix_encoder(name: str, verify_only: bool) -> bool:
    d = BASE_MODELS_DIR / "sentance_encoder"
    complete = (d / "modules.json").exists() and (d / "config.json").exists() and any(d.glob("*.safetensors")) | any(d.glob("pytorch_model.bin"))
    if not complete and not verify_only:
        _snapshot(name, d)
        (d / "SOURCE.txt").write_text(name + "\n", encoding="utf-8")
    try:
        from sentence_transformers import SentenceTransformer  # noqa: WPS433

        m = SentenceTransformer(str(d), device="cpu")
        v = m.encode(["LOTO nahi kiya, panel live tha", "panel was not isolated"], normalize_embeddings=True)
        log.info("encoder OK: dim %d, sim(hinglish, english) = %.3f", v.shape[1], float(v[0] @ v[1]))
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("encoder NOT loadable: %s", str(exc)[:200])
        return False


def fix_nli(verify_only: bool) -> bool:
    d = BASE_MODELS_DIR / "bert"
    if not (d / "config.json").exists() and not verify_only:
        _snapshot(NLI_DEFAULT, d, allow=["config.json", "*.json", "*.model", "*.safetensors", "*.txt"])
        (d / "SOURCE.txt").write_text(NLI_DEFAULT + "\n", encoding="utf-8")
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: WPS433

        AutoTokenizer.from_pretrained(str(d))
        AutoModelForSequenceClassification.from_pretrained(str(d))
        log.info("NLI model OK (%s)", d.name)
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("NLI model NOT loadable: %s", str(exc)[:200])
        return False


def fix_gliner(verify_only: bool) -> bool:
    d = BASE_MODELS_DIR / "gliner_multi"
    if not (d / "gliner_config.json").exists() and not verify_only:
        _snapshot(GLINER_HUB, d)
    # GLiNER loads its backbone through AutoModel/AutoTokenizer, so the mDeBERTa config.json must sit
    # next to gliner_config.json - without its "model_type" key transformers cannot identify the
    # architecture ("Unrecognized model ... should have a `model_type` key").
    needs = not (d / "config.json").exists() or not (d / "tokenizer_config.json").exists() \
        or (d / "tokenizer_config.json").stat().st_size < 200
    if needs and not verify_only:
        _snapshot(GLINER_BACKBONE, d, allow=["config.json", "tokenizer*", "spm.model",
                                             "special_tokens_map.json", "added_tokens.json"])
    try:
        from gliner import GLiNER  # noqa: WPS433
        from .finetune.tokenization import install_splitter  # noqa: WPS433

        m = GLiNER.from_pretrained(str(d))
        install_splitter(m)
        ents = m.predict_entities("Worker at 6 m without harness, no fall occurred", ["energy source", "control absent", "negation word"], threshold=0.3)
        log.info("GLiNER OK, zero-shot sample: %s", [(e["text"], e["label"]) for e in ents][:6])
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("GLiNER NOT loadable: %s", str(exc)[:200])
        return False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--encoder", default=ENCODER_DEFAULT)
    ap.add_argument("--skip-nli", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    results = {"encoder": fix_encoder(a.encoder, a.verify), "gliner": fix_gliner(a.verify)}
    if not a.skip_nli:
        results["nli"] = fix_nli(a.verify)
    (MODELS_DIR / "models_status.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
