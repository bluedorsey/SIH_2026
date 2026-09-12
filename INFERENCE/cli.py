"""Command line:

    python -m INFERENCE.cli "Monkey board se tool box neeche gira, niche 2 log the, barricading nahi tha"
    python -m INFERENCE.cli --file reports.txt --out results.jsonl     # one report per line
    python -m INFERENCE.cli --no-models "..."                          # rules only, no model load
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .pipeline import analyse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SIF precursor analysis")
    ap.add_argument("text", nargs="?", help="the observation text")
    ap.add_argument("--file", help="a file with one observation per line")
    ap.add_argument("--out", help="write JSONL here instead of stdout")
    ap.add_argument("--report-id")
    ap.add_argument("--no-models", action="store_true", help="rules only (no GLiNER / heads)")
    ap.add_argument("--compact", action="store_true", help="one line per result")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING,
                        format="%(levelname)-7s %(name)s: %(message)s")

    if a.file:
        texts = [ln.strip() for ln in Path(a.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    elif a.text:
        texts = [a.text]
    else:
        ap.error("give a text or --file")

    results = [analyse(t, report_id=a.report_id if len(texts) == 1 else None,
                       use_models=not a.no_models) for t in texts]

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{len(results)} result(s) -> {a.out}")
    else:
        for r in results:
            print(json.dumps(r, ensure_ascii=False, indent=None if a.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
