from foolsearch.normalize import compact, normalize_text, romaji_to_kana


def test_fullwidth_and_case():
    assert normalize_text("ＴＡＮＡＫＡ") == "tanaka"


def test_katakana_becomes_hiragana():
    assert compact("タナカ") == compact("たなか")


def test_small_kana_unified():
    assert compact("がっこう") == compact("がつこう")


def test_long_vowel_mark_ignored():
    assert compact("パスワード") == compact("パスワド")


def test_romaji_to_kana():
    assert romaji_to_kana("tanaka") == "たなか"
    assert romaji_to_kana("satou") == "さとう"
    assert romaji_to_kana("suzuki") == "すずき"


def test_romaji_rejects_non_romaji():
    assert romaji_to_kana("1234") is None
    assert romaji_to_kana("たなか") is None
