"""Mã số thuế (tax code) structure and checksum.

Shapes in use:
- 10 digits: an organisation, or an individual registered before 1/7/2025. The 10th digit is a
  mod-11 check digit over the first nine with weights 31, 29, 23, 19, 17, 13, 7, 5, 3.
- 13 digits, usually written NNNNNNNNNN-BBB: a dependent unit (branch). The first ten carry the
  same checksum and the 3-digit suffix is 001-999.
- 12 digits: since 1/7/2025 an individual's tax code is their số định danh cá nhân
  (Thông tư 86/2024/TT-BTC). It has no checksum, only the CCCD structure, so it is a much
  weaker check than the 10-digit one.
"""

from __future__ import annotations

import re

from .ids import parse_cccd
from .result import Check, match, mismatch, undetermined

MST_WEIGHTS = (31, 29, 23, 19, 17, 13, 7, 5, 3)

_STRIP = re.compile(r"[\s.]")
_BASE10 = re.compile(r"[0-9]{10}")
_BRANCH13 = re.compile(r"([0-9]{10})-?([0-9]{3})")
_PERSONAL12 = re.compile(r"[0-9]{12}")


def mst_check_digit(first9: str) -> int | None:
    """Expected 10th digit, or None when no digit can be valid (remainder gives 10)."""
    if not re.fullmatch(r"[0-9]{9}", first9):
        raise ValueError(f"need 9 digits, got {first9!r}")
    digit = (10 - sum(w * int(d) for w, d in zip(MST_WEIGHTS, first9, strict=True)) % 11) % 11
    return None if digit == 10 else digit


def _check_base10(base: str) -> None:
    expected = mst_check_digit(base[:9])
    if expected is None:
        raise ValueError("first nine digits admit no valid check digit")
    if int(base[9]) != expected:
        raise ValueError(f"check digit is {base[9]}, expected {expected}")


def parse_mst(text: str) -> str:
    """Return the MST kind ('base10', 'branch13', 'personal12'); raise ValueError if invalid."""
    s = _STRIP.sub("", text)
    if _BASE10.fullmatch(s):
        _check_base10(s)
        return "base10"
    if m := _BRANCH13.fullmatch(s):
        _check_base10(m.group(1))
        if m.group(2) == "000":
            raise ValueError("branch suffix 000 is not assigned")
        return "branch13"
    if _PERSONAL12.fullmatch(s):
        parse_cccd(s)
        return "personal12"
    raise ValueError(f"{text!r} is not a 10-, 12- or 13-digit tax code")


def check_mst(text: str, verifier: str = "V_MST") -> Check:
    if not _STRIP.sub("", text):
        return undetermined(verifier, "empty")
    try:
        kind = parse_mst(text)
    except ValueError as exc:
        return mismatch(verifier, str(exc))
    return match(verifier, kind)
