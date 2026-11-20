"""Vietnamese number words ("bằng chữ") and the digits-vs-words verifier.

Money on invoices, receipts and tax forms is written twice, in digits and in words. The two are
produced by the same hand (or template) but are read by OCR independently, so agreement is
strong evidence that both readings are right, and a grammar violation in the words is evidence
that the words were misread.

The parser is deliberately strict. It accepts the formal written forms and a few common
variants (một/mốt, bốn/tư, lăm/nhăm, linh/lẻ, nghìn/ngàn, tỷ/tỉ) and rejects anything whose
value is ambiguous in speech:
- "mười năm" / "hai mươi năm": after mười/mươi, five must be "lăm" (or "nhăm");
- "một trăm năm": colloquially 150, formally needs "một trăm năm mươi" or "một trăm linh năm";
- "một nghìn năm": colloquially 1500; a bare digit directly after a scale word is rejected.
"""

from __future__ import annotations

import re
import unicodedata

from .result import Check, match, mismatch, undetermined
from .text import clean

DIGIT = {
    "không": 0,
    "một": 1,
    "hai": 2,
    "ba": 3,
    "bốn": 4,
    "năm": 5,
    "sáu": 6,
    "bảy": 7,
    "bẩy": 7,
    "tám": 8,
    "chín": 9,
}
# Units after "mười" (11-19) and after "mươi" (x1-x9). "năm" is not allowed: it must be "lăm".
AFTER_MUOI = {k: v for k, v in DIGIT.items() if v > 0 and k != "năm"} | {"tư": 4, "lăm": 5, "nhăm": 5}
AFTER_MUOI_TENS = AFTER_MUOI | {"mốt": 1}
AFTER_LINH = {k: v for k, v in DIGIT.items() if v > 0} | {"tư": 4}
LINH = {"linh", "lẻ"}
SCALES = {"nghìn": 10**3, "ngàn": 10**3, "triệu": 10**6, "tỷ": 10**9, "tỉ": 10**9}
TRAILING = {"đồng", "chẵn", "vnđ", "vnd", "việt", "nam"}


def _tens(tok: list[str]) -> int:
    """1-99 written without hundreds: mười ..., X mươi ..., (never a bare digit)."""
    if tok[0] == "mười":
        if len(tok) == 1:
            return 10
        if len(tok) == 2 and tok[1] in AFTER_MUOI:
            return 10 + AFTER_MUOI[tok[1]]
    elif len(tok) >= 2 and tok[1] == "mươi" and DIGIT.get(tok[0], 0) >= 2:
        if len(tok) == 2:
            return DIGIT[tok[0]] * 10
        if len(tok) == 3 and tok[2] in AFTER_MUOI_TENS:
            return DIGIT[tok[0]] * 10 + AFTER_MUOI_TENS[tok[2]]
    raise ValueError(f"ill-formed tens: {' '.join(tok)!r}")


def _group(tok: list[str], first: bool, tail: bool) -> int:
    """0-999. `first`: no higher group precedes. `tail`: directly follows a scale word, last."""
    if "trăm" in tok:
        if tok.index("trăm") != 1 or tok[0] not in DIGIT:
            raise ValueError(f"ill-formed hundreds: {' '.join(tok)!r}")
        hundreds = DIGIT[tok[0]]
        if hundreds == 0 and first:
            raise ValueError("leading 'không trăm'")
        rest = tok[2:]
        if not rest:
            return hundreds * 100
        if rest[0] in LINH:
            if len(rest) == 2 and rest[1] in AFTER_LINH:
                return hundreds * 100 + AFTER_LINH[rest[1]]
            raise ValueError(f"ill-formed 'linh': {' '.join(rest)!r}")
        if len(rest) == 1 and rest[0] in DIGIT:
            raise ValueError(f"bare digit after 'trăm' is ambiguous: {' '.join(tok)!r}")
        return hundreds * 100 + _tens(rest)
    if tok[0] in LINH:
        if first or len(tok) != 2 or tok[1] not in AFTER_LINH:
            raise ValueError(f"ill-formed 'linh': {' '.join(tok)!r}")
        return AFTER_LINH[tok[1]]
    if len(tok) == 1 and tok[0] in DIGIT:
        if tail:
            raise ValueError(f"bare digit after a scale word is ambiguous: {tok[0]!r}")
        return DIGIT[tok[0]]
    return _tens(tok)


def _parse(tok: list[str], first: bool, tail: bool) -> int:
    if not tok:
        raise ValueError("empty number")
    for value in (10**9, 10**6, 10**3):
        positions = [i for i, t in enumerate(tok) if SCALES.get(t) == value]
        if not positions:
            continue
        i = positions[-1]
        left, right = tok[:i], tok[i + 1 :]
        if not left:
            raise ValueError(f"scale word {tok[i]!r} without a multiplier")
        high = _parse(left, first, tail=False)
        if high == 0:
            raise ValueError(f"zero multiplier before {tok[i]!r}")
        if value < 10**9 and high >= 1000:
            raise ValueError(f"multiplier {high} too large before {tok[i]!r}")
        low = _parse(right, first=False, tail=True) if right else 0
        if low >= value:
            raise ValueError(f"{low} after {tok[i]!r} overflows")
        return high * value + low
    return _group(tok, first, tail)


def parse_number_words(text: str) -> int:
    """Parse Vietnamese number words to an int; raise ValueError on ill-formed input."""
    tok = clean(text).split()
    while tok and tok[-1] in TRAILING:
        tok.pop()
    unknown = [t for t in tok if t not in DIGIT and t not in AFTER_MUOI_TENS and t not in SCALES]
    unknown = [t for t in unknown if t not in LINH and t not in {"mười", "mươi", "trăm"}]
    if unknown:
        raise ValueError(f"not number words: {unknown}")
    return _parse(tok, first=True, tail=False)


_CURRENCY = re.compile(r"\s*(đồng|vnđ|vnd|đ)\s*$")
_PLAIN = re.compile(r"[0-9]+")
_GROUPED = re.compile(r"[0-9]{1,3}(?:([.,])[0-9]{3})(?:\1[0-9]{3})*")


def parse_amount_digits(text: str) -> int:
    """'1.230.000', '1,230,000', '1 230 000', '1230000 đ' -> 1230000. VND has no decimals,
    but a zero fraction (',00' after dot grouping, '.00' after comma grouping) is tolerated."""
    s = _CURRENCY.sub("", unicodedata.normalize("NFC", text).strip().lower()).replace(" ", "")
    if _PLAIN.fullmatch(s):
        return int(s)
    for sep, dec in ((".", ","), (",", ".")):
        head, _, frac = s.partition(dec)
        if frac and not re.fullmatch(r"0{1,2}", frac):
            continue
        if _PLAIN.fullmatch(head) or ((m := _GROUPED.fullmatch(head)) and m.group(1) == sep):
            return int(head.replace(sep, ""))
    raise ValueError(f"not an amount: {text!r}")


def check_amount(digits: str, words: str, verifier: str = "V_MONEY_WORDS") -> Check:
    """Digits and words must state the same amount. Either side unparsable is a MISMATCH:
    the gate cannot accept it, and it is a real detected anomaly (for error-detection recall)."""
    if not digits.strip() or not clean(words):
        return undetermined(verifier, "missing digits or words")
    try:
        a = parse_amount_digits(digits)
    except ValueError as exc:
        return mismatch(verifier, f"digits: {exc}")
    try:
        b = parse_number_words(words)
    except ValueError as exc:
        return mismatch(verifier, f"words: {exc}")
    if a != b:
        return mismatch(verifier, f"digits {a} != words {b}")
    return match(verifier)


_UNITS = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")


def number_to_words(
    n: int,
    *,
    thousand: str = "nghìn",
    linh: str = "linh",
    one_after_tens: str = "mốt",
    four_after_tens: str = "tư",
    five: str = "lăm",
) -> str:
    """Formal Vietnamese words for n >= 0, the inverse of `parse_number_words`.

    After a scale word every lower group is written with its hundreds ("một triệu không trăm
    linh năm nghìn"); groups that are entirely zero are skipped. Keyword arguments select the
    accepted variants (ngàn, lẻ, một, bốn, nhăm) so that renderings can vary without changing
    the value.
    """
    if n < 0:
        raise ValueError("negative amounts are not written in words")
    scales = ((10**9, "tỷ"), (10**6, "triệu"), (10**3, thousand))

    def tens_units(v: int, after_hundreds: bool) -> list[str]:
        t, u = divmod(v, 10)
        if t == 0:
            if u == 0:
                return []
            return [linh, _UNITS[u]] if after_hundreds else [_UNITS[u]]
        out = ["mười"] if t == 1 else [_UNITS[t], "mươi"]
        if u == 5:
            out.append(five)
        elif u == 1 and t > 1:
            out.append(one_after_tens)
        elif u == 4 and t > 1:
            out.append(four_after_tens)
        elif u:
            out.append(_UNITS[u])
        return out

    def group(v: int, first: bool) -> list[str]:
        h, rest = divmod(v, 100)
        if first and h == 0:
            return tens_units(rest, after_hundreds=False)
        return [_UNITS[h], "trăm", *tens_units(rest, after_hundreds=True)]

    def words(v: int, first: bool) -> list[str]:
        for value, name in scales:
            if v >= value:
                high, low = divmod(v, value)
                out = [*words(high, first), name]
                if low:
                    out += words(low, first=False)
                return out
        return group(v, first)

    return "không" if n == 0 else " ".join(words(n, first=True))
