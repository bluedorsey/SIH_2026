"""
Zip everything Colab needs into one bundle (data + TRAINING package + optional base GLiNER).

    python -m TRAINING.pack_for_colab                 # -> sih_train_bundle.zip at repo root (~5-20 MB without base model)
    python -m TRAINING.pack_for_colab --with-gliner-base   # also include SERVER/Classfication/Models/gliner_multi (~1.1 GB)

Never includes .env, RAW data, checkpoints or __pycache__.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "TRAINING"  # noqa: A001

from .config import BASE_MODELS_DIR, DISTILLED_DIR, GOLD_JSONL, IHM_JSONL, REPO_ROOT, TRAINING_DIR  # noqa: E402

SKIP_DIRS = {"__pycache__", "checkpoints", ".ipynb_checkpoints"}


def _add_tree(z: zipfile.ZipFile, root: Path, rel_root: Path) -> int:
    n = 0
    for p in sorted(root.rglob("*")):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.parts) or p.name == ".env":
            continue
        z.write(p, str(p.relative_to(rel_root)).replace("\\", "/"))
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO_ROOT / "sih_train_bundle.zip"))
    ap.add_argument("--with-gliner-base", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        n = _add_tree(z, TRAINING_DIR, REPO_ROOT)
        for sub in ("gliner", "setfit"):
            d = DISTILLED_DIR / sub
            if d.exists():
                n += _add_tree(z, d, REPO_ROOT)
        for f in (DISTILLED_DIR / "train.jsonl", DISTILLED_DIR / "dev.jsonl", DISTILLED_DIR / "test.jsonl", DISTILLED_DIR / "gliner_labels.json", GOLD_JSONL, IHM_JSONL):
            if f.exists():
                z.write(f, str(f.relative_to(REPO_ROOT)).replace("\\", "/"))
                n += 1
        if a.with_gliner_base and (BASE_MODELS_DIR / "gliner_multi").exists():
            n += _add_tree(z, BASE_MODELS_DIR / "gliner_multi", REPO_ROOT)
    print(f"{out}  ({n} files, {out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
