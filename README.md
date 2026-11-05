# FoolSearch

A foolproof keyword search engine for support-desk style lookups:
type very few keywords, make small typos, still get ranked candidates.

- Standard library only, in-memory, starts instantly
- Works with a single fragment: part of a name, one kanji, the last
  4 digits of a phone number
- Typo tolerant: one wrong kanji/kana, a missing character, voiced
  sound confusion, katakana vs hiragana, romaji instead of kana
- Every hit explains itself (which field, which signal matched)

## Install

```bash
pip install -e .
```

## Use as a library

```python
from foolsearch import SearchEngine

engine = SearchEngine()
engine.add_documents([
    {"id": "c001", "fields": {
        "name": "田中太郎", "reading": "たなかたろう",
        "phone": "090-1234-5678", "tags": "配送",
        "memo": "配送先を変更したい"}},
])

for r in engine.search("たなか"):        # fragment is enough
    print(r.score, r.document.fields["name"], r.matches)
for r in engine.search("佐籐"):          # one wrong kanji still hits 佐藤
    ...
for r in engine.search("5678"):          # phone last 4 digits
    ...
```

Records are generic: any `fields` dict works. Field weights default to
name/reading/phone = 3.0, alias = 2.5, email/tags = 2.0, memo = 1.0,
anything else = 1.0, and can be overridden via
`SearchEngine(field_weights={...})`.

## Use from the command line

```bash
python -m foolsearch --sample "さとう けん"   # bundled fictional data
python -m foolsearch data.json "たなか"       # your JSON records
python -m foolsearch data.json                # interactive loop
```

The JSON format is a list of `{"id": ..., "fields": {...}}` records
(a flat object also works: every key except `id` becomes a field).

## How matching works

Each query term is scored against each field with several signals and
the best one wins per term: exact token, field/token prefix, substring,
character n-gram overlap, edit-distance fuzzy (including a windowed
variant for long Japanese strings), and digit substring. Terms are
summed, with a bonus for matching more of the typed terms, so adding a
second keyword narrows the ranking instead of filtering everything out
when one term misses.

Normalization runs first: NFKC, lowercase, katakana to hiragana,
small-kana unification, long-vowel marks dropped. Romaji terms are also
converted to kana (`tanaka` finds たなか).

## Tests and demo

```bash
pip install pytest
python -m pytest
python examples/demo.py
```

Sample data in `src/foolsearch/sample_data.json` is entirely fictional.
