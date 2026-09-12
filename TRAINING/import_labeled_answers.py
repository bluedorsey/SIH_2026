"""
Import a chatbot's JSON reply into DATA/distilled/raw/label.jsonl, using the SAME validator
as the API pipeline, and linking every row back to the seed it came from (so the next
`extract_for_labeling` run knows what is done).

    python -m TRAINING.import_labeled_answers reply.json
    python -m TRAINING.import_labeled_answers reply.json --dry-run     # check without writing
    python -m TRAINING.import_labeled_answers reply1.json reply2.json  # several at once

Accepts: a JSON array, a single object, several arrays separated by blank lines, ```json fences,
or a file with one JSON object per line.  Rows the validator refuses go to label.rejects.jsonl
with the reason, and are re-offered by the next extract run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "TRAINING"  # noqa: A001

from .config import DISTILLED_RAW_DIR, TEACHER_INPUT  # noqa: E402
from .distill.backends import extract_json, parse_array_lenient  # noqa: E402
from .distill.schema import validate_many  # noqa: E402


def _seed_pool() -> tuple[dict, dict]:
    """input_id -> seed row, and normalised text -> seed row (chatbots often drop the id)."""
    by_id, by_text = {}, {}
    with open(TEACHER_INPUT, "r", encoding="utf-8") as fh:
        for ln in fh:
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get("teacher_prompt") != "label":
                continue
            by_id[r["input_id"]] = r
            by_text[" ".join((r.get("text") or "").split()).lower()] = r
    return by_id, by_text


def _elements(paths: list[Path]) -> list[dict]:
    """Everything JSON-ish in the given files, tolerating fences, several arrays, or one-per-line."""
    out: list[dict] = []
    for p in paths:
        if not p.exists():
            raise SystemExit(f"{p} not found")
        raw = p.read_text(encoding="utf-8").strip()
        if not raw:
            print(f"warning: {p} is empty", file=sys.stderr)
            continue
        got = extract_json(raw, expect="array")
        if not got:
            got, dropped = parse_array_lenient(raw)
            if got:
                print(f"note: {p.name} was not strict JSON - kept {len(got)} element(s), {dropped} unreadable",
                      file=sys.stderr)
        if not got:                                    # last resort: one JSON object per line
            got = []
            for ln in raw.splitlines():
                ln = ln.strip().rstrip(",")
                if ln.startswith("{"):
                    try:
                        got.append(json.loads(ln))
                    except json.JSONDecodeError:
                        pass
        if not got:
            raise SystemExit(f"{p}: no JSON array/objects found (first 200 chars: {raw[:200]!r})")
        rows = [g for g in got if isinstance(g, dict)]
        # chatbots like to append a summary/notes object at the end of the array - an annotation
        # always carries the narrative text, so anything without it is not a row
        extra = [g for g in rows if "text" not in g]
        if extra:
            keys = sorted({k for g in extra for k in g})[:6]
            print(f"note: ignored {len(extra)} element(s) in {p.name} with no \"text\" field "
                  f"(keys: {', '.join(keys)}) - not annotations", file=sys.stderr)
        out += [g for g in rows if "text" in g]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="import chatbot-labelled rows into label.jsonl")
    ap.add_argument("files", nargs="+", help="the chatbot's JSON reply file(s)")
    ap.add_argument("--dry-run", action="store_true", help="validate and report, write nothing")
    ap.add_argument("--model", default="chatbot", help="name recorded as the teacher (e.g. chatgpt, gemini)")
    a = ap.parse_args(argv)

    items = _elements([Path(f) for f in a.files])
    by_id, by_text = _seed_pool()
    meta = {"teacher": "manual", "model": a.model, "batch_id": "manual"}
    # validate_element overwrites input_id with its kwarg, so remember what the chatbot echoed
    echoed = [it.get("input_id") if isinstance(it, dict) else None for it in items]

    ok, bad = validate_many(items, source="label:manual", **meta)

    kept, unmatched = [], 0
    for r in ok:
        hint = echoed[r["batch_pos"]] if r.get("batch_pos") is not None and r["batch_pos"] < len(echoed) else None
        seed = by_id.get(hint or "") or by_text.get(" ".join((r.get("text") or "").split()).lower())
        if seed is None:
            bad.append({"problems": ["annotated text matches no seed row (the chatbot rewrote it, "
                                     "or the input_id was not copied)"], "text": (r.get("text") or "")[:120], **meta})
            unmatched += 1
            continue
        r["input_id"] = r["seed_id"] = seed["input_id"]
        r["source"] = f"label:{seed['source']}"
        kept.append(r)

    print(f"{len(kept)} row(s) accepted, {len(bad)} rejected"
          + (f" ({unmatched} because the text did not match any seed)" if unmatched else ""))
    for r in bad[:12]:
        print("  REJECTED: " + "; ".join(r.get("problems") or [])[:220])
    if len(bad) > 12:
        print(f"  ... and {len(bad) - 12} more")

    if a.dry_run:
        print("(dry run - nothing written)")
        return 0

    DISTILLED_RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows_path = DISTILLED_RAW_DIR / "label.jsonl"
    with open(rows_path, "a", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(DISTILLED_RAW_DIR / "label.rejects.jsonl", "a", encoding="utf-8") as fh:
        for r in bad:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    total = sum(1 for ln in open(rows_path, "r", encoding="utf-8") if ln.strip())
    print(f"label.jsonl now holds {total} rows")
    print("next chunk: python -m TRAINING.extract_for_labeling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
