"""Dates in the forms Vietnamese administrative documents use, and their comparison.

Accepted:
- numeric: 15/03/2018, 15-3-2018, 15.03.2018, 03/2018, 2018;
- labelled: "ngày 15 tháng 3 năm 2018", "Hà Nội, ngày 15 tháng 03 năm 2018";
- words (birth certificates): "ngày mười lăm tháng ba năm hai nghìn không trăm mười tám";
- blanks left on a template: "ngày .... tháng .... năm 2018" gives day and month None.

"năm" is both the year label and the digit five ("tháng năm năm ..." is May). The label is the
first "năm" after "tháng" for which the month and the year on either side both parse.
"""

from __future__ import annotations

import calendar
import re
import unicodedata
from dataclasses import dataclass

from .number_words import parse_number_words
from .result import Check, match, mismatch, undetermined
from .text import clean

_DMY = re.compile(r"(?<![0-9])([0-9]{1,2})\s*([/.\-])\s*([0-9]{1,2})\s*\2\s*([0-9]{4})(?![0-9])")
_MY = re.compile(r"(?<![0-9])([0-9]{1,2})\s*[/.\-]\s*([0-9]{4})(?![0-9])")
_Y = re.compile(r"\s*([0-9]{4})\s*")
_DAY_PREFIX = {"mồng", "mùng"}


@dataclass(frozen=True)
class PartialDate:
    year: int | None = None
    month: int | None = None
    day: int | None = None

    def __post_init__(self) -> None:
        if self.year is not None and not 1000 <= self.year <= 2999:
            raise ValueError(f"year {self.year} out of range")
        if self.month is not None and not 1 <= self.month <= 12:
            raise ValueError(f"month {self.month} out of range")
        if self.day is not None:
            # Without a year, allow 29 February (2000 is a leap year).
            last = calendar.monthrange(self.year or 2000, self.month)[1] if self.month else 31
            if not 1 <= self.day <= last:
                raise ValueError(f"day {self.day} out of range")

    def components(self) -> dict[str, int]:
        return {k: v for k, v in (("year", self.year), ("month", self.month), ("day", self.day)) if v is not None}

    def __str__(self) -> str:
        def part(v: int | None, width: int) -> str:
            return "." * width if v is None else f"{v:0{width}d}"

        return f"{part(self.day, 2)}/{part(self.month, 2)}/{part(self.year, 4)}"


def _value(tok: list[str]) -> int | None:
    if not tok:
        return None
    if all(t.isdigit() for t in tok):  # "20 18": a printed "20" followed by handwritten "18"
        return int("".join(tok))
    if tok == ["tư"]:  # "tháng tư" is how April is written; "tư" is not a standalone number word
        return 4
    return parse_number_words(" ".join(tok))


def _labelled(tok: list[str]) -> PartialDate:
    day: int | None = None
    if "ngày" in tok:
        start = tok.index("ngày") + 1
        if "tháng" not in tok[start:]:
            raise ValueError("'ngày' without 'tháng'")
        end = tok.index("tháng", start)
        day_tok = [t for t in tok[start:end] if t not in _DAY_PREFIX]
        day = _value(day_tok)
        tok = tok[end:]
    if tok and tok[0] == "tháng":
        errors = []
        for j in [i for i, t in enumerate(tok) if t == "năm" and i > 0]:
            try:
                return PartialDate(year=_value(tok[j + 1 :]), month=_value(tok[1:j]), day=day)
            except ValueError as exc:
                errors.append(str(exc))
        raise ValueError(f"no reading of 'tháng ... năm ...' parses: {errors}")
    if "năm" in tok:
        return PartialDate(year=_value(tok[tok.index("năm") + 1 :]), day=day)
    raise ValueError("no date labels")


def parse_date(text: str) -> PartialDate:
    raw = unicodedata.normalize("NFC", text).lower()
    if m := _DMY.search(raw):
        return PartialDate(year=int(m.group(4)), month=int(m.group(3)), day=int(m.group(1)))
    if m := _MY.search(raw):
        return PartialDate(year=int(m.group(2)), month=int(m.group(1)))
    if m := _Y.fullmatch(raw):
        return PartialDate(year=int(m.group(1)))
    return _labelled(clean(raw).split())


def compare_dates(a: str | PartialDate, b: str | PartialDate, verifier: str = "V_DATE") -> Check:
    """MATCH only when both state the same components and they agree.

    One side giving fewer components (year only vs a full date) is UNDETERMINED: the shared
    part agreeing is not evidence for the rest.
    """
    try:
        da = a if isinstance(a, PartialDate) else parse_date(a)
        db = b if isinstance(b, PartialDate) else parse_date(b)
    except ValueError as exc:
        return mismatch(verifier, f"unparsable: {exc}")
    ca, cb = da.components(), db.components()
    shared = ca.keys() & cb.keys()
    if not shared:
        return undetermined(verifier, "no component stated on both sides")
    differing = sorted(k for k in shared if ca[k] != cb[k])
    if differing:
        swapped = {"day", "month"} <= shared and ca["day"] == cb["month"] and ca["month"] == cb["day"]
        return mismatch(verifier, "day/month swapped" if swapped else f"differs in {', '.join(differing)}")
    if ca.keys() != cb.keys():
        return undetermined(verifier, f"agree on {', '.join(sorted(shared))} only")
    return match(verifier)
