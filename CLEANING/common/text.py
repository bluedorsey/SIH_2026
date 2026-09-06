"""
Text normalisation helpers.

Design rule: the cleaned `text` of a record is what the teacher LLM and
GLiNER will see, and GLiNER spans must be verbatim substrings of it.
So we normalise *encoding artefacts* (whitespace, unicode, PDF wraps,
curly quotes) but we NEVER "fix" the author's wording, spelling or
grammar - typos and Hinglish are part of the target distribution.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

# characters that carry no meaning and break span matching
_ZERO_WIDTH = "".join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD))
_ZW_RE = re.compile(f"[{re.escape(_ZERO_WIDTH)}]")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_QUOTE_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "′": "'", "″": '"',
}
_DASH_MAP = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-",  # hyphen, nb-hyphen, figure dash, en dash
    "—": " - ", "―": " - ",                               # em dash, horizontal bar
    "−": "-",                                                  # minus sign
}
_BULLET_RE = re.compile(r"^[•‣◦⁃∙·▪●\-\*]\s*", re.M)
_WS_RE = re.compile("[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def normalize_unicode(s: str) -> str:
    """NFKC-normalise, strip zero-width/control chars, straighten quotes and dashes.

    Devanagari and other scripts are left intact (NFKC only composes
    combining marks, it does not transliterate).
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = _ZW_RE.sub("", s)
    s = _CTRL_RE.sub("", s)
    for k, v in _QUOTE_MAP.items():
        s = s.replace(k, v)
    for k, v in _DASH_MAP.items():
        s = s.replace(k, v)
    return s


def collapse_ws(s: str, keep_newlines: bool = False) -> str:
    """Collapse runs of horizontal whitespace; optionally keep line breaks."""
    if not s:
        return ""
    if keep_newlines:
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        lines = [_WS_RE.sub(" ", ln).strip() for ln in s.split("\n")]
        s = "\n".join(lines)
        s = _MULTI_NL_RE.sub("\n\n", s)
        return s.strip()
    s = _WS_RE.sub(" ", s.replace("\r", " ").replace("\n", " "))
    return re.sub(r" {2,}", " ", s).strip()


def clean_text(s: str, keep_newlines: bool = False) -> str:
    """Full normalisation used for every free-text field."""
    return collapse_ws(normalize_unicode(s), keep_newlines=keep_newlines)


# --------------------------------------------------------------------------
# PDF line re-flow
# --------------------------------------------------------------------------
_LIST_ITEM_RE = re.compile(r"^(?:[•‣◦⁃∙·▪●]|\(?\d{1,2}[\.\)]|[a-z][\.\)]|[-\*])\s+")


def reflow_pdf_lines(lines: list[str]) -> str:
    """Join hard-wrapped PDF lines back into paragraphs.

    - a line that starts with a bullet / "1." / "a)" starts a new line
    - a line ending in "/" or "-" is joined to the next without a space
      (IOGP wraps at "tools/equipment/\\nmaterials" and "first-\\ndegree")
    - everything else is joined with a single space
    """
    out: list[str] = []
    buf = ""
    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        if _LIST_ITEM_RE.match(ln) or not buf:
            if buf:
                out.append(buf)
            buf = ln
            continue
        if buf.endswith(("/", "-")):
            buf = buf + ln
        else:
            buf = buf + " " + ln
    if buf:
        out.append(buf)
    return "\n".join(out)


# --------------------------------------------------------------------------
# Hashing / keys
# --------------------------------------------------------------------------
# keep letters/digits/whitespace and all combining marks (Devanagari matras are category Mc/Mn, not \w)
_PUNCT_RE = re.compile("[^\\w\\s\u0300-\u036f\u0900-\u097f]", re.UNICODE)


def dedup_key(s: str) -> str:
    """Aggressive normalisation used ONLY for duplicate detection (never stored as text)."""
    s = normalize_unicode(s or "").lower()
    s = _PUNCT_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sha1(s: str, n: int = 12) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]


def word_count(s: str) -> int:
    return len((s or "").split())
