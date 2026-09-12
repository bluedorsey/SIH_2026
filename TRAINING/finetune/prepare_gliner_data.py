"""
DATA/distilled/{train,dev,test}.jsonl -> GLiNER training format

    python -m TRAINING.finetune.prepare_gliner_data
    -> DATA/distilled/gliner/{train,dev,test}.json   list of {"tokenized_text": [...], "ner": [[start_tok, end_tok, label], ...]}
       DATA/distilled/gliner/labels.json             the natural-language label names (what GLiNER sees)
       DATA/distilled/gliner/stats.json

- spans come from schema.py (char offsets, verbatim) and are mapped to token indices with the Indic-aware splitter
- role names are replaced by natural-language labels (config.ROLE_TO_GLINER_LABEL) - GLiNER matches label semantics
- the same span may carry two labels (e.g. outcome + not-released) - both are kept
- spans that do not align to token boundaries or exceed MAX_SPAN_TOKENS are dropped and counted
- rows without any span are kept as negatives (GLiNER benefits from them) unless --drop-empty
- optional --weak: also include DATA/distilled/gliner/weak_train.json produced by weak_label_gliner.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.finetune"  # noqa: A001

from ..config import DISTILLED_DIR, MAX_SPAN_TOKENS, MAX_TEXT_TOKENS, ROLE_TO_GLINER_LABEL  # noqa: E402
from .tokenization import char_span_to_tokens, tokenize  # noqa: E402

OUT_DIR = DISTILLED_DIR / "gliner"


def convert(rows: list[dict], drop_empty: bool = False) -> tuple[list[dict], Counter]:
    out, stats = [], Counter()
    for r in rows:
        toks = tokenize(r["text"])
        if not toks or len(toks) > MAX_TEXT_TOKENS:
            stats["dropped_len"] += 1
            continue
        ner: set[tuple[int, int, str]] = set()
        for s in r.get("spans", []):
            span = char_span_to_tokens(toks, s["start"], s["end"])
            if span is None:
                stats["span_misaligned"] += 1
                continue
            if span[1] - span[0] + 1 > MAX_SPAN_TOKENS:
                stats["span_too_wide"] += 1
                continue
            ner.add((span[0], span[1], ROLE_TO_GLINER_LABEL[s["role"]]))
            stats[f"label:{s['role']}"] += 1
        if not ner and drop_empty:
            stats["dropped_empty"] += 1
            continue
        out.append({"tokenized_text": [t for t, _, _ in toks], "ner": [list(x) for x in sorted(ner)],
                    "id": r.get("id"), "seed_id": r.get("seed_id"), "verdict": r.get("verdict"), "lang": r.get("lang")})
        stats["rows"] += 1
        stats["rows_with_spans"] += bool(ner)
    return out, stats



# roles the raw incident reports almost never state - a weak row that carries none of them adds
# energy/outcome signal the model already has plenty of, and dilutes the balanced teacher rows.
_SCARCE_LABELS = {"control absent", "control ineffective", "control present",
                  "pseudo control", "person exposed", "not released yet"}


def balance_weak(weak: list[dict], real: list[dict], max_ratio: float = 0.5) -> tuple[list[dict], dict]:
    """Keep weak rows that carry a scarce role, capped so weak never outnumbers real by `max_ratio`.

    Weak labelling reads raw incident narratives, which state the energy and the outcome but
    rarely a barrier: unfiltered it contributed 14 845 energy_cue spans against 13 control_absent,
    i.e. 73 % of the training signal pushing the model to ignore barriers entirely.
    """
    useful = [w for w in weak if any(lbl in _SCARCE_LABELS for _, _, lbl in w.get("ner", []))]
    cap = int(len(real) * max_ratio)
    useful.sort(key=lambda w: -sum(1 for _, _, lbl in w["ner"] if lbl in _SCARCE_LABELS))
    kept = useful[:cap]
    return kept, {"weak_seen": len(weak), "weak_with_scarce_role": len(useful),
                  "weak_kept": len(kept), "weak_cap": cap}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop-empty", action="store_true", help="drop rows without any span (default: keep as negatives)")
    ap.add_argument("--weak", action="store_true", help="append weak_train.json from weak_label_gliner.py to train")
    ap.add_argument("--weak-all", action="store_true",
                    help="append EVERY weak row (old behaviour - floods the set with energy_cue spans)")
    ap.add_argument("--weak-ratio", type=float, default=0.5,
                    help="max weak rows as a fraction of real rows (default 0.5)")
    a = ap.parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_stats = {}
    for split in ("train", "dev", "test"):
        p = DISTILLED_DIR / f"{split}.jsonl"
        rows = [json.loads(ln) for ln in open(p, "r", encoding="utf-8")] if p.exists() else []
        data, stats = convert(rows, drop_empty=a.drop_empty)
        if split == "train" and a.weak and (OUT_DIR / "weak_train.json").exists():
            weak = json.loads((OUT_DIR / "weak_train.json").read_text(encoding="utf-8"))
            if not a.weak_all:
                weak, wstats = balance_weak(weak, data, a.weak_ratio)
                stats.update(wstats)
            data += weak
            stats["weak_rows_added"] = len(weak)
        (OUT_DIR / f"{split}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        all_stats[split] = dict(stats)
        print(f"{split:5} {len(data):6} rows  spans {sum(len(d['ner']) for d in data):6}  {dict((k, v) for k, v in stats.items() if not k.startswith('label:'))}")
    (OUT_DIR / "labels.json").write_text(json.dumps(sorted(set(ROLE_TO_GLINER_LABEL.values())), indent=2), encoding="utf-8")
    (OUT_DIR / "stats.json").write_text(json.dumps(all_stats, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
