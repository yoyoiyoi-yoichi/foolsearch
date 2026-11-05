"""Text normalization for Japanese / English mixed search text.

The goal is forgiving matching: differences in character width, kana type,
small kana and casing should not change what a query hits.
"""
from __future__ import annotations

import re
import unicodedata

_SMALL_KANA = {
    "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
    "ゃ": "や", "ゅ": "ゆ", "ょ": "よ", "っ": "つ", "ゎ": "わ", "ゖ": "け",
}

_NON_WORD = re.compile(r"[^0-9a-zぁ-ん一-龥]+")


def _katakana_to_hiragana(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:  # ァ..ヶ -> ぁ..ゖ
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def normalize_text(text: str) -> str:
    """Normalize to a comparable form: NFKC, lowercase, hiragana, no symbols."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text)).lower()
    text = _katakana_to_hiragana(text)
    text = "".join(_SMALL_KANA.get(ch, ch) for ch in text)
    text = text.replace("ー", "")
    text = _NON_WORD.sub(" ", text)
    return " ".join(text.split())


def compact(text: str) -> str:
    """Normalized text with all separators removed (one Japanese 'word')."""
    return normalize_text(text).replace(" ", "")


def digits_only(text: str) -> str:
    return re.sub(r"\D", "", unicodedata.normalize("NFKC", str(text or "")))


# --- romaji -> hiragana -------------------------------------------------
_ROMAJI3 = {
    "shi": "し", "chi": "ち", "tsu": "つ", "sha": "しや", "shu": "しゆ",
    "sho": "しよ", "cha": "ちや", "chu": "ちゆ", "cho": "ちよ",
    "jya": "じや", "jyu": "じゆ", "jyo": "じよ", "ja": "じや", "ju": "じゆ",
    "jo": "じよ",
}
_ROMAJI2 = {
    "ka": "か", "ki": "き", "ku": "く", "ke": "け", "ko": "こ",
    "sa": "さ", "si": "し", "su": "す", "se": "せ", "so": "そ",
    "ta": "た", "ti": "ち", "tu": "つ", "te": "て", "to": "と",
    "na": "な", "ni": "に", "nu": "ぬ", "ne": "ね", "no": "の",
    "ha": "は", "hi": "ひ", "hu": "ふ", "fu": "ふ", "he": "へ", "ho": "ほ",
    "ma": "ま", "mi": "み", "mu": "む", "me": "め", "mo": "も",
    "ya": "や", "yu": "ゆ", "yo": "よ",
    "ra": "ら", "ri": "り", "ru": "る", "re": "れ", "ro": "ろ",
    "wa": "わ", "wo": "を",
    "ga": "が", "gi": "ぎ", "gu": "ぐ", "ge": "げ", "go": "ご",
    "za": "ざ", "zi": "じ", "zu": "ず", "ze": "ぜ", "zo": "ぞ",
    "da": "だ", "di": "ぢ", "du": "づ", "de": "で", "do": "ど",
    "ba": "ば", "bi": "び", "bu": "ぶ", "be": "べ", "bo": "ぼ",
    "pa": "ぱ", "pi": "ぴ", "pu": "ぷ", "pe": "ぺ", "po": "ぽ",
    "ji": "じ", "fu": "ふ",
}
_VOWELS = {"a": "あ", "i": "い", "u": "う", "e": "え", "o": "お"}


def romaji_to_kana(text: str) -> str | None:
    """Best-effort romaji -> hiragana. Returns None if input is not romaji-like."""
    s = re.sub(r"[^a-z]", "", (text or "").lower())
    if len(s) < 2 or not s.isascii():
        return None
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "n" and (i == len(s) - 1 or s[i + 1] not in "aiueoy"):
            out.append("ん")
            i += 1
            continue
        if i + 1 < len(s) and s[i] == s[i + 1] and s[i] not in "aiueon":
            out.append("つ")  # doubled consonant -> small tsu (normalized later)
            i += 1
            continue
        tri = s[i:i + 3]
        if tri in _ROMAJI3:
            out.append(_ROMAJI3[tri])
            i += 3
            continue
        duo = s[i:i + 2]
        if duo in _ROMAJI2:
            out.append(_ROMAJI2[duo])
            i += 2
            continue
        if s[i] in _VOWELS:
            out.append(_VOWELS[s[i]])
            i += 1
            continue
        return None
    kana = "".join(out)
    return "".join(_SMALL_KANA.get(ch, ch) for ch in kana)
