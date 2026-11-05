"""Tokenizing and character n-grams.

Japanese text has no word boundaries, so in addition to whitespace tokens
we index character bigrams/trigrams of the compact form. N-gram overlap is
what keeps a query useful even when a character is wrong or missing.
"""
from __future__ import annotations

from .normalize import compact, normalize_text


def split_terms(query: str) -> list[str]:
    """Split a raw query into normalized terms (full-width space safe)."""
    return [t for t in normalize_text(query).split(" ") if t]


def tokens_of(text: str) -> list[str]:
    return [t for t in normalize_text(text).split(" ") if t]


def char_ngrams(text: str, sizes: tuple[int, ...] = (2, 3)) -> set[str]:
    s = compact(text)
    grams: set[str] = set()
    for n in sizes:
        if len(s) >= n:
            grams.update(s[i:i + n] for i in range(len(s) - n + 1))
    if 0 < len(s) < 2:
        grams.add(s)
    return grams
