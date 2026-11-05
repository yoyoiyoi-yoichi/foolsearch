"""Tiny demo: a few keywords, a typo, a phone fragment."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from foolsearch import SearchEngine

records = json.loads(
    (Path(__file__).parent.parent / "src" / "foolsearch" / "sample_data.json").read_text(encoding="utf-8")
)
engine = SearchEngine()
engine.add_documents(records)

for query in ["たなか", "タナカ", "tanaka", "佐籐", "さとう けん", "5678", "パスワド"]:
    print(f"query: {query}")
    for r in engine.search(query, limit=3):
        why = ", ".join(f"{m.term}->{m.field}:{m.signal}" for m in r.matches)
        print(f"  {r.score:6.1f}  {r.document.fields['name']}  [{why}]")
    print()
