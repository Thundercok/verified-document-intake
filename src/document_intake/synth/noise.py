"""OCR-like corruptions of Vietnamese text and digits.

One call applies one edit and names it, so missed errors can be traced to the edit type. The
edits are the confusions reported for Vietnamese OCR and handwriting: tone marks (the most
frequent), the letter diacritics of ă â ê ô ơ ư đ, dropped letters and syllables, merged words,
look-alike digits, and digit deletion, duplication and transposition.

This is a stand-in for real OCR output, not a model of it: it fixes the edit types but not their
real frequencies, and real errors are often several edits at once.
"""

from __future__ import annotations

import random
import unicodedata
from dataclasses import dataclass

from ..verify.text import TONE_MARKS

_TONES = tuple(TONE_MARKS)
_LETTER_MARKS = ("̂", "̆", "̛")  # circumflex, breve, horn
_VOWELS = set("aeiouyAEIOUY")
DIGIT_CONFUSIONS = {
    "0": "86",
    "8": "03",
    "6": "05",
    "1": "7",
    "7": "12",
    "3": "8",
    "5": "6",
    "2": "7",
    "4": "9",
    "9": "4",
}
NUMBER_CONFUSIONS = {"lăm": "năm", "năm": "lăm", "mươi": "mười", "mười": "mươi", "sáu": "sau"}


@dataclass(frozen=True)
class Corruption:
    text: str
    op: str


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _pick_word(words: list[str], rng: random.Random, ok) -> int | None:
    idx = [i for i, w in enumerate(words) if ok(w)]
    return rng.choice(idx) if idx else None


def tone_change(text: str, rng: random.Random) -> str | None:
    words = text.split(" ")
    i = _pick_word(words, rng, lambda w: any(c in TONE_MARKS for c in unicodedata.normalize("NFD", w)))
    if i is None:
        return None
    nfd = unicodedata.normalize("NFD", words[i])
    old = next(c for c in nfd if c in TONE_MARKS)
    new = rng.choice([t for t in _TONES if t != old] + [""])
    words[i] = _nfc(nfd.replace(old, new, 1))
    return " ".join(words)


def tone_add(text: str, rng: random.Random) -> str | None:
    words = text.split(" ")
    i = _pick_word(
        words,
        rng,
        lambda w: not any(c in TONE_MARKS for c in unicodedata.normalize("NFD", w)) and any(c in _VOWELS for c in w),
    )
    if i is None:
        return None
    nfd = unicodedata.normalize("NFD", words[i])
    j = next(k for k, c in enumerate(nfd) if c in _VOWELS)
    while j + 1 < len(nfd) and unicodedata.combining(nfd[j + 1]):
        j += 1
    words[i] = _nfc(nfd[: j + 1] + rng.choice(_TONES) + nfd[j + 1 :])
    return " ".join(words)


def diacritic_drop(text: str, rng: random.Random) -> str | None:
    nfd = unicodedata.normalize("NFD", text)
    idx = [k for k, c in enumerate(nfd) if c in _LETTER_MARKS or c in "đĐ"]
    if not idx:
        return None
    k = rng.choice(idx)
    repl = {"đ": "d", "Đ": "D"}.get(nfd[k], "")
    return _nfc(nfd[:k] + repl + nfd[k + 1 :])


def letter_drop(text: str, rng: random.Random) -> str | None:
    idx = [k for k, c in enumerate(text) if c.isalpha() and k + 1 < len(text) and text[k + 1].isalpha()]
    if not idx:
        return None
    k = rng.choice(idx)
    return text[:k] + text[k + 1 :]


def syllable_drop(text: str, rng: random.Random) -> str | None:
    words = text.split(" ")
    if len(words) < 2:
        return None
    del words[rng.randrange(len(words))]
    return " ".join(words)


def space_merge(text: str, rng: random.Random) -> str | None:
    idx = [k for k, c in enumerate(text) if c == " "]
    if not idx:
        return None
    k = rng.choice(idx)
    return text[:k] + text[k + 1 :]


def number_confusion(text: str, rng: random.Random) -> str | None:
    words = text.split(" ")
    i = _pick_word(words, rng, lambda w: w.lower() in NUMBER_CONFUSIONS)
    if i is None:
        return None
    new = NUMBER_CONFUSIONS[words[i].lower()]
    words[i] = new.capitalize() if words[i][:1].isupper() else new
    return " ".join(words)


def digit_confusion(text: str, rng: random.Random) -> str | None:
    idx = [k for k, c in enumerate(text) if c in DIGIT_CONFUSIONS]
    if not idx:
        return None
    k = rng.choice(idx)
    return text[:k] + rng.choice(DIGIT_CONFUSIONS[text[k]]) + text[k + 1 :]


def digit_delete(text: str, rng: random.Random) -> str | None:
    idx = [k for k, c in enumerate(text) if c.isdigit()]
    if len(idx) < 2:
        return None
    k = rng.choice(idx)
    return text[:k] + text[k + 1 :]


def digit_duplicate(text: str, rng: random.Random) -> str | None:
    idx = [k for k, c in enumerate(text) if c.isdigit()]
    if not idx:
        return None
    k = rng.choice(idx)
    return text[: k + 1] + text[k] + text[k + 1 :]


def digit_transpose(text: str, rng: random.Random) -> str | None:
    idx = [k for k in range(len(text) - 1) if text[k].isdigit() and text[k + 1].isdigit() and text[k] != text[k + 1]]
    if not idx:
        return None
    k = rng.choice(idx)
    return text[:k] + text[k + 1] + text[k] + text[k + 2 :]


TEXT_OPS = (tone_change, tone_add, diacritic_drop, letter_drop, syllable_drop, space_merge)
DIGIT_OPS = (digit_confusion, digit_delete, digit_duplicate, digit_transpose)
OPS = {
    "text": TEXT_OPS,
    "digits": DIGIT_OPS,
    "words": (*TEXT_OPS, number_confusion, number_confusion),  # confusables weighted up
    "mixed": (*TEXT_OPS, *DIGIT_OPS),
}


def corrupt(text: str, rng: random.Random, kind: str) -> Corruption | None:
    """Apply one random applicable edit of the given kind; None if no edit changes the text."""
    ops = list(OPS[kind])
    rng.shuffle(ops)
    for op in ops:
        out = op(text, rng)
        if out is not None and out != text:
            return Corruption(out, op.__name__)
    return None
