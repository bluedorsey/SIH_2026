"""IOGP Life-Saving Rule name normalisation."""
from __future__ import annotations

import re

from ..config import LSR_ALIASES, LSR_CANONICAL, LSR_NO_RULE_VALUES

_SPLIT_RE = re.compile(r"\s*(?:/|;|,|\band\b|&|\+)\s*", re.I)


def _is_no_rule(key: str) -> bool:
    key = re.sub(r"\s+", " ", key.lower()).strip(" .")
    return key in LSR_NO_RULE_VALUES or key.replace("–", "-") in LSR_NO_RULE_VALUES


def canonical_lsr(raw: str | None) -> str | None:
    """Map one raw rule string to its canonical IOGP name (or None)."""
    if raw is None:
        return None
    s = str(raw).strip()
    key = re.sub(r"\s+", " ", s.lower()).strip(" .")
    if _is_no_rule(key):
        return None
    if key in LSR_ALIASES:
        return LSR_ALIASES[key]
    # tolerate trailing words like "Line of fire (dropped object)"
    key2 = re.sub(r"\(.*?\)", "", key).strip()
    if key2 in LSR_ALIASES:
        return LSR_ALIASES[key2]
    for canon in LSR_CANONICAL:
        if canon.lower() in key:
            return canon
    return None


def canonical_lsr_list(raw: str | list | None) -> tuple[list[str], list[str]]:
    """Normalise a raw rule value (string, possibly with several rules, or list).

    Returns (canonical_list, unmapped_raw_values).
    """
    if raw is None:
        return [], []
    parts: list[str]
    if isinstance(raw, (list, tuple)):
        parts = [str(p) for p in raw]
    else:
        parts = [p for p in _SPLIT_RE.split(str(raw)) if p]
    out: list[str] = []
    unmapped: list[str] = []
    for p in parts:
        c = canonical_lsr(p)
        if c is None:
            if p.strip() and not _is_no_rule(p):
                unmapped.append(p.strip())
        elif c not in out:
            out.append(c)
    return out, unmapped
