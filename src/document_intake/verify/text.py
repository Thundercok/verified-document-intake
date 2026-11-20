"""Vietnamese text normalisation and name comparison.

Two spellings of the same Vietnamese word can differ in ways that are not errors:
- Unicode form: precomposed (NFC) "ế" vs decomposed (NFD) "e" + U+0302 + U+0301.
- Tone placement: old style "hòa", "thúy", "khỏe" vs new style "hoà", "thuý", "khoẻ".
- Case: "NGUYỄN VĂN AN" (birth certificates write names in capitals) vs "Nguyễn Văn An".

`syllable_key` maps a syllable to (letters without tone, tone), which removes all three at once:
the tone is a property of the syllable, wherever it is drawn.
"""

from __future__ import annotations

import re
import unicodedata

from .result import Check, match, mismatch, undetermined

# Combining marks that carry tone. Other combining marks (circumflex U+0302, breve U+0306,
# horn U+031B) are part of the letter, not the tone.
TONE_MARKS = {
    "̀": "huyền",
    "́": "sắc",
    "̃": "ngã",
    "̉": "hỏi",
    "̣": "nặng",
}

_NON_LETTER = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")


def clean(text: str) -> str:
    """NFC, lower-case, punctuation to spaces, single spaces. Icelandic eth (a common OCR
    substitute for Đ) is mapped to đ."""
    text = unicodedata.normalize("NFC", text).lower().replace("ð", "đ")
    text = _NON_LETTER.sub(" ", text)
    return _SPACE.sub(" ", text).strip()


def syllable_key(syllable: str) -> tuple[str, str]:
    """(letters without tone, tone name or ''). Raises ValueError on two tone marks."""
    nfd = unicodedata.normalize("NFD", syllable.lower())
    tones = [TONE_MARKS[c] for c in nfd if c in TONE_MARKS]
    if len(tones) > 1:
        raise ValueError(f"syllable {syllable!r} carries {len(tones)} tone marks")
    base = unicodedata.normalize("NFC", "".join(c for c in nfd if c not in TONE_MARKS))
    return base, tones[0] if tones else ""


def text_key(text: str) -> tuple[tuple[str, str], ...]:
    return tuple(syllable_key(s) for s in clean(text).split())


def fold_diacritics(text: str) -> str:
    """Strip every diacritic, including đ -> d. Lossy: for lookup keys, never for verification."""
    nfd = unicodedata.normalize("NFD", clean(text).replace("đ", "d"))
    return "".join(c for c in nfd if not unicodedata.combining(c))


def compare_names(a: str, b: str, verifier: str = "V_NAME") -> Check:
    """Compare two renderings of a person's name.

    MATCH only when every syllable has the same letters and the same tone. A difference that
    disappears when diacritics are folded is reported separately: it is the typical OCR or
    handwriting confusion (Nguyễn/Nguyến, Thủy/Thùy) and must NOT be accepted, but a reviewer
    can fix it in one keystroke.
    """
    if not clean(a) or not clean(b):
        return undetermined(verifier, "empty name")
    try:
        ka, kb = text_key(a), text_key(b)
    except ValueError as exc:
        return mismatch(verifier, str(exc))
    if ka == kb:
        return match(verifier)
    if fold_diacritics(a) == fold_diacritics(b):
        return mismatch(verifier, "differs only in diacritics")
    if len(ka) != len(kb):
        return mismatch(verifier, f"{len(ka)} vs {len(kb)} syllables")
    return mismatch(verifier)
