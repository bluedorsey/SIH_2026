"""
DATA/distilled/{train,dev,test}.jsonl -> sentence-level label files for the SetFit / MiniLM heads

    python -m TRAINING.finetune.prepare_setfit_data
    -> DATA/distilled/setfit/{train,dev,test}.jsonl   {"text", "prefilter", "verdict", "statement_type", "lsr": [...], "lang", "seed_id"}
       DATA/distilled/setfit/stats.json

Heads (prompts.md "How the outputs feed the two fine-tunes"):
  prefilter       binary  1 = needs the full pipeline (any SIF-relevant verdict, incl. INSUFFICIENT -> review),
                          0 = LOW_ENERGY / NON_EVENT
  verdict         9-class EEI verdict (optional head, mostly for the demo)
  statement_type  6-class
  lsr             multi-label over the 9 IOGP rules
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.finetune"  # noqa: A001

from ..config import DISTILLED_DIR, LSR_NAMES  # noqa: E402

OUT_DIR = DISTILLED_DIR / "setfit"
NEG_VERDICTS = {"LOW_ENERGY", "NON_EVENT"}


def convert(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append({
            "text": r["text"],
            "prefilter": 0 if r["verdict"] in NEG_VERDICTS else 1,
            "verdict": r["verdict"],
            "statement_type": r["statement_type"],
            "lsr": [l for l in r.get("life_saving_rules", []) if l in LSR_NAMES],
            "lang": r.get("lang"), "seed_id": r.get("seed_id"), "id": r.get("id"), "source": r.get("source"),
        })
    return out


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = {}
    for split in ("train", "dev", "test"):
        p = DISTILLED_DIR / f"{split}.jsonl"
        rows = [json.loads(ln) for ln in open(p, "r", encoding="utf-8")] if p.exists() else []
        data = convert(rows)
        with open(OUT_DIR / f"{split}.jsonl", "w", encoding="utf-8") as fh:
            for d in data:
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
        stats[split] = {"rows": len(data), "prefilter": dict(Counter(d["prefilter"] for d in data)),
                        "verdict": dict(Counter(d["verdict"] for d in data)), "statement_type": dict(Counter(d["statement_type"] for d in data)),
                        "lsr": dict(Counter(l for d in data for l in d["lsr"])), "lang": dict(Counter(d["lang"] for d in data))}
        print(split, stats[split]["rows"], "prefilter", stats[split]["prefilter"], "verdict", stats[split]["verdict"])
    (OUT_DIR / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
