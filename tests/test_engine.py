import json
from pathlib import Path

import pytest

from foolsearch import SearchEngine

DATA = json.loads(
    (Path(__file__).parent.parent / "src" / "foolsearch" / "sample_data.json").read_text(encoding="utf-8")
)


@pytest.fixture(scope="module")
def engine():
    e = SearchEngine()
    e.add_documents(DATA)
    return e


def top_id(engine, query):
    results = engine.search(query, limit=5)
    assert results, f"no results for {query!r}"
    return results[0].id


def test_name_fragment_kana(engine):
    assert top_id(engine, "たなか") == "c001"


def test_name_fragment_kanji(engine):
    assert top_id(engine, "田中") == "c001"


def test_katakana_query(engine):
    assert top_id(engine, "タナカ") == "c001"


def test_romaji_query(engine):
    assert top_id(engine, "tanaka") == "c001"


def test_single_character_is_enough(engine):
    ids = [r.id for r in engine.search("田", limit=5)]
    assert "c001" in ids


def test_typo_missing_last_kana(engine):
    assert top_id(engine, "たなかたろ") == "c001"


def test_typo_one_wrong_kanji(engine):
    # 佐藤 typed with a wrong second kanji
    assert top_id(engine, "佐籐") == "c002"


def test_typo_voiced_confusion(engine):
    assert top_id(engine, "だなか") == "c001"


def test_phone_last_four_digits(engine):
    assert top_id(engine, "5678") == "c001"


def test_two_terms_narrow_down(engine):
    assert top_id(engine, "さとう けん") == "c003"
    assert top_id(engine, "さとう はなこ") == "c002"


def test_memo_keyword(engine):
    assert top_id(engine, "パスワード") == "c004"


def test_memo_keyword_with_typo(engine):
    assert top_id(engine, "パスワド") == "c004"


def test_no_match_returns_empty(engine):
    assert engine.search("zzzqqq") == []


def test_result_explains_itself(engine):
    (result,) = engine.search("たなか", limit=1)
    assert result.matches
    assert result.matches[0].signal
