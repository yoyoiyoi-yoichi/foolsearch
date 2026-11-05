"""FoolSearch engine: hybrid *lexical* search over small in-memory records.

Several weak signals are combined and ranked, instead of requiring one
exact match (the same idea as hybrid search, kept inside keyword search):

  exact token / prefix / substring / character n-gram overlap /
  edit-distance fuzzy (incl. windowed fuzzy for long Japanese strings) /
  digit substring (e.g. the last 4 digits of a phone number)

A single short keyword is enough to get candidates, a typo costs score
but does not zero the result, and every hit explains which signal fired
so an operator can trust (or dismiss) it at a glance while on a call.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping

from .distance import levenshtein
from .normalize import compact, digits_only, normalize_text, romaji_to_kana
from .tokenize import char_ngrams, split_terms, tokens_of

DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "name": 3.0,
    "reading": 3.0,
    "alias": 2.5,
    "phone": 3.0,
    "email": 2.0,
    "tags": 2.0,
    "memo": 1.0,
}
DEFAULT_WEIGHT = 1.0
MIN_SCORE = 2.0


@dataclass
class Document:
    id: str
    fields: dict[str, str]
    payload: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class Match:
    term: str
    field: str
    signal: str


@dataclass
class SearchResult:
    document: Document
    score: float
    matches: list[Match] = dc_field(default_factory=list)

    @property
    def id(self) -> str:
        return self.document.id


@dataclass
class _FieldIndex:
    name: str
    weight: float
    tokens: list[str]
    compact: str
    ngrams: set[str]
    digits: str


@dataclass
class _DocIndex:
    document: Document
    fields: list[_FieldIndex]


def _allowed_dist(term: str) -> int:
    return 1 if len(term) <= 5 else 2


def _window_fuzzy(term: str, text: str, max_dist: int) -> bool:
    """True if some window of text is within max_dist edits of term.

    Windows are the term's length or one longer (a shorter window makes
    almost anything match a 2-3 character term). For 2-character terms
    only a window at the field start counts, which keeps a mistyped
    family name (佐籐 vs 佐藤...) useful without matching everywhere.
    """
    n = len(term)
    for size in {n, n + 1}:
        if size <= 0 or size > len(text):
            continue
        starts = (0,) if n == 2 else range(len(text) - size + 1)
        for i in starts:
            if levenshtein(term, text[i:i + size], max_dist) <= max_dist:
                return True
    return False


class SearchEngine:
    def __init__(self, field_weights: Mapping[str, float] | None = None):
        self.field_weights = dict(DEFAULT_FIELD_WEIGHTS)
        if field_weights:
            self.field_weights.update(field_weights)
        self._docs: list[_DocIndex] = []
        self._token_df: dict[str, int] = {}

    # -- indexing ---------------------------------------------------------
    def add_document(self, doc: Document | Mapping[str, Any]) -> None:
        if isinstance(doc, Mapping):
            fields = {str(k): str(v) for k, v in doc.get("fields", {}).items()}
            payload = dict(doc.get("payload", {}))
            if not fields:  # flat mapping style: every key but id is a field
                fields = {str(k): str(v) for k, v in doc.items() if k != "id"}
            doc = Document(id=str(doc["id"]), fields=fields, payload=payload)
        findexes = []
        for fname, value in doc.fields.items():
            findexes.append(_FieldIndex(
                name=fname,
                weight=self.field_weights.get(fname, DEFAULT_WEIGHT),
                tokens=tokens_of(value),
                compact=compact(value),
                ngrams=char_ngrams(value),
                digits=digits_only(value),
            ))
            for tok in set(tokens_of(value)):
                self._token_df[tok] = self._token_df.get(tok, 0) + 1
        self._docs.append(_DocIndex(document=doc, fields=findexes))

    def add_documents(self, docs: Iterable[Document | Mapping[str, Any]]) -> None:
        for doc in docs:
            self.add_document(doc)

    def __len__(self) -> int:
        return len(self._docs)

    # -- scoring ----------------------------------------------------------
    def _idf(self, token: str) -> float:
        df = self._token_df.get(token, 0)
        return 1.0 + math.log((len(self._docs) + 1) / (df + 1))

    def _score_field(self, term: str, variants: list[str], fidx: _FieldIndex) -> tuple[float, str | None]:
        best, signal = 0.0, None

        def consider(score: float, name: str) -> None:
            nonlocal best, signal
            if score > best:
                best, signal = score, name

        term_digits = digits_only(term)
        digit_bonus = 0.0
        if len(term_digits) >= 3 and term_digits in fidx.digits:
            digit_bonus = 6.0 if fidx.digits.endswith(term_digits) else 4.0
            signal = "digits_suffix" if digit_bonus == 6.0 else "digits"

        for variant in variants:
            if not variant:
                continue
            if variant in fidx.tokens:
                consider(10.0 * self._idf(variant), "exact")
            if len(variant) >= 2 and any(t.startswith(variant) for t in fidx.tokens):
                consider(6.5, "prefix")
            if variant and variant in fidx.compact:
                # substring of the whole field: the classic few-keyword hit
                ratio = len(variant) / max(len(fidx.compact), 1)
                consider(6.0 + 3.0 * min(ratio, 1.0), "substring")
            if fidx.compact.startswith(variant) and len(variant) >= 2:
                consider(8.0, "field_prefix")
            # fuzzy against single tokens
            limit = _allowed_dist(variant)
            for tok in fidx.tokens:
                if abs(len(tok) - len(variant)) <= limit and levenshtein(variant, tok, limit) <= limit:
                    consider(6.0 - levenshtein(variant, tok, limit), "fuzzy")
                    break
            # windowed fuzzy: catches one wrong kanji inside a longer name
            if len(variant) >= 2 and len(fidx.compact) > len(variant):
                if _window_fuzzy(variant, fidx.compact, 1):
                    consider(5.0, "fuzzy_window")
            # n-gram overlap: degrades gracefully as typos increase
            grams = char_ngrams(variant)
            if grams and fidx.ngrams:
                containment = len(grams & fidx.ngrams) / len(grams)
                if containment > 0:
                    consider(5.0 * containment, "ngram")
        if digit_bonus:
            # additive, so a suffix match (last-4 phone lookup) outranks
            # the same digits appearing in the middle of the number
            best += digit_bonus
        return best * fidx.weight, signal

    # -- search -------------------------------------------------------------
    def search(self, query: str, limit: int = 10, min_score: float = MIN_SCORE) -> list[SearchResult]:
        terms = split_terms(query)
        if not terms:
            return []
        results: list[SearchResult] = []
        for didx in self._docs:
            total, matches, hit_terms = 0.0, [], 0
            for term in terms:
                variants = [term]
                kana = romaji_to_kana(term)
                if kana and kana != term:
                    variants.append(kana)
                best, best_field, best_signal = 0.0, None, None
                for fidx in didx.fields:
                    score, signal = self._score_field(term, variants, fidx)
                    if score > best:
                        best, best_field, best_signal = score, fidx.name, signal
                if best > 0 and best_field is not None:
                    hit_terms += 1
                    total += best
                    matches.append(Match(term=term, field=best_field, signal=best_signal or ""))
            if hit_terms:
                # reward matching more of the few terms the operator typed
                total *= 0.5 + 0.5 * (hit_terms / len(terms))
                if total >= min_score:
                    results.append(SearchResult(document=didx.document, score=round(total, 3), matches=matches))
        results.sort(key=lambda r: (-r.score, r.id))
        return results[:limit]
