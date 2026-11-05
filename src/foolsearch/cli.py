"""Command line for trying FoolSearch on a support desk.

Usage:
  python -m foolsearch data.json "たなか"          # one-shot
  python -m foolsearch data.json                   # interactive loop
  python -m foolsearch --sample "さとう 1234"      # bundled sample data

The JSON file is a list of records: {"id": ..., "fields": {name, reading,
phone, tags, memo, ...}} (a flat object also works: every key but id is
treated as a searchable field).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import SearchEngine

SAMPLE = Path(__file__).with_name("sample_data.json")


def load_engine(path: Path) -> SearchEngine:
    records = json.loads(path.read_text(encoding="utf-8"))
    engine = SearchEngine()
    engine.add_documents(records)
    return engine


def show(engine: SearchEngine, query: str, limit: int = 5) -> None:
    results = engine.search(query, limit=limit)
    if not results:
        print("  (no candidates)")
        return
    for r in results:
        fields = r.document.fields
        label = fields.get("name") or r.id
        why = ", ".join(f"{m.term}->{m.field}:{m.signal}" for m in r.matches)
        print(f"  {r.score:6.1f}  {label}  [{why}]")
        extra = {k: v for k, v in fields.items() if k not in ("name",)}
        if extra:
            print("         " + " / ".join(f"{k}: {v}" for k, v in extra.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="foolsearch")
    parser.add_argument("data", nargs="?", help="JSON file of records")
    parser.add_argument("query", nargs="*", help="search words (one-shot)")
    parser.add_argument("--sample", action="store_true", help="use bundled sample data")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    if args.sample and args.data and not args.query:
        # `foolsearch --sample たなか`: the word lands in the data slot
        args.query = [args.data]
        args.data = None

    if args.sample:
        engine = load_engine(SAMPLE)
    elif args.data:
        engine = load_engine(Path(args.data))
    else:
        parser.error("give a data file or --sample")

    if args.query:
        show(engine, " ".join(args.query), args.limit)
        return 0
    print("Type a few keywords (name fragment, phone last digits...). Ctrl-C to quit.")
    try:
        while True:
            query = input("search> ").strip()
            if query:
                show(engine, query, args.limit)
    except (KeyboardInterrupt, EOFError):
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
