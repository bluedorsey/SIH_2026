"""File I/O helpers - always UTF-8, always Windows-safe."""
from __future__ import annotations

import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Iterable

log = logging.getLogger("clean.io")


def _open_for_write(path: Path, **kw):
    """Open for writing; if Windows has the file locked (open in Excel), fall back to '<name>.new<ext>'."""
    try:
        return open(path, "w", **kw)
    except PermissionError:
        alt = path.with_name(path.stem + ".new" + path.suffix)
        log.warning("%s is locked (open in Excel?) - writing %s instead", path.name, alt.name)
        return open(alt, "w", **kw)


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def file_sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> int:
    ensure_dir(path.parent)
    n = 0
    with _open_for_write(path, encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def write_json(obj: Any, path: Path) -> None:
    ensure_dir(path.parent)
    with _open_for_write(path, encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)


def write_csv(rows: list[dict[str, Any]], path: Path, columns: list[str] | None = None) -> int:
    """Write a list of flat dicts to CSV (utf-8-sig so Excel opens it correctly)."""
    ensure_dir(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return 0
    cols = columns or list({k: None for r in rows for k in r.keys()}.keys())
    with _open_for_write(path, encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            flat = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v) for k, v in r.items()}
            w.writerow(flat)
    return len(rows)
