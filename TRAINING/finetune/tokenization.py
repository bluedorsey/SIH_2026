"""
Word splitter shared by data prep, training and inference.

GLiNER's default WhitespaceTokenSplitter uses r"\\w+(?:[-_]\\w+)*|\\S".  Python's \\w does not include
Devanagari / Bengali-Assamese vowel signs (Unicode category Mc/Mn), so "मिस्त्री" would become several
"words" and a 4-word Hindi span could exceed GLiNER's max_width of 12.  This splitter keeps Indic words
whole and is installed on the model at train AND inference time (`install_splitter(model)`), so span
widths mean the same thing in the validator (TRAINING/distill/schema.py), in training data and in production.
"""
from __future__ import annotations

import re
from typing import Iterator

WORD_RE = re.compile(r"[\wऀ-ॿঀ-৿]+(?:[-_][\wऀ-ॿঀ-৿]+)*|\S", re.UNICODE)


class IndicWordSplitter:
    """Same call signature as gliner.data_processing.tokenizer.WhitespaceTokenSplitter."""

    def __call__(self, text: str) -> Iterator[tuple[str, int, int]]:
        for m in WORD_RE.finditer(text):
            yield m.group(), m.start(), m.end()


def tokenize(text: str) -> list[tuple[str, int, int]]:
    return list(IndicWordSplitter()(text))


def char_span_to_tokens(tokens: list[tuple[str, int, int]], start: int, end: int) -> tuple[int, int] | None:
    """Map a char span to (first_token_idx, last_token_idx) inclusive; None if it does not align to token edges."""
    first = last = None
    for i, (_, s, e) in enumerate(tokens):
        if s <= start < e or (first is None and s >= start and s < end):
            if first is None:
                first = i
        if s < end <= e or (s >= start and e <= end):
            last = i
    if first is None or last is None or last < first:
        return None
    return first, last


def install_splitter(model) -> None:
    """Replace the GLiNER model's word splitter with the Indic-aware one (idempotent)."""
    try:
        model.data_processor.words_splitter = IndicWordSplitter()
    except AttributeError:  # older gliner versions
        try:
            model.processor.words_splitter = IndicWordSplitter()
        except AttributeError:
            pass
