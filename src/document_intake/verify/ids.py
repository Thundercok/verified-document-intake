"""CCCD / số định danh cá nhân: structure, and consistency with the holder's other fields.

Layout (Thông tư 07/2016/TT-BCA, Điều 7):
- digits 1-3: province where the birth was registered (vn_admin.CCCD_PROVINCE_CODES);
- digit 4: century of birth and sex, 0/1 = 1900s male/female, 2/3 = 2000s, 4/5 = 2100s, ...;
- digits 5-6: last two digits of the birth year;
- digits 7-12: random.

There is no check digit, so a single substituted digit in the last six is undetectable. The
first six digits, however, restate three facts that the same document (or a birth certificate)
states again: birth year, sex and place of birth registration. Those cross-checks are what make
the number verifiable at all.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .address import parse_address
from .dates import parse_date
from .result import Check, match, mismatch, undetermined
from .text import fold_diacritics
from .vn_admin import CCCD_PROVINCE_CODES, OLD_TO_NEW, PROVINCES_POST_2025

_STRIP = re.compile(r"[\s.\-]")


@dataclass(frozen=True)
class Cccd:
    number: str
    province: str  # pre-2025 province of birth registration
    sex: str  # "nam" | "nữ"
    birth_year: int


def parse_cccd(text: str, today: date | None = None) -> Cccd:
    """Parse a 12-digit CCCD; raise ValueError on any structural violation."""
    s = _STRIP.sub("", text)
    if not re.fullmatch(r"[0-9]{12}", s):
        raise ValueError(f"CCCD must be 12 digits, got {len(s)} characters")
    province = CCCD_PROVINCE_CODES.get(s[:3])
    if province is None:
        raise ValueError(f"unassigned province code {s[:3]}")
    d = int(s[3])
    year = 1900 + (d // 2) * 100 + int(s[4:6])
    if year > (today or date.today()).year:
        raise ValueError(f"birth year {year} is in the future")
    return Cccd(s, province, "nam" if d % 2 == 0 else "nữ", year)


def check_cccd_format(text: str, verifier: str = "V_CCCD_FORMAT") -> Check:
    if not _STRIP.sub("", text):
        return undetermined(verifier, "empty")
    try:
        parse_cccd(text)
    except ValueError as exc:
        return mismatch(verifier, str(exc))
    return match(verifier)


def _normalise_sex(text: str) -> str | None:
    return {"nam": "nam", "nu": "nữ"}.get(fold_diacritics(text))


def check_cccd_consistency(
    number: str,
    *,
    birth_date: str | None = None,
    sex: str | None = None,
    birth_registration_place: str | None = None,
) -> list[Check]:
    """Cross-check the CCCD prefix against fields stated elsewhere.

    `birth_registration_place` must be the place of birth *registration* (nơi đăng ký khai
    sinh), not quê quán: the two differ for most people.
    """
    try:
        card = parse_cccd(number)
    except ValueError as exc:
        return [mismatch("V_CCCD_FORMAT", str(exc))]
    checks = [match("V_CCCD_FORMAT")]

    if birth_date is not None:
        try:
            year = parse_date(birth_date).year
        except ValueError as exc:
            checks.append(mismatch("V_CCCD_YEAR", f"birth date unparsable: {exc}"))
        else:
            if year is None:
                checks.append(undetermined("V_CCCD_YEAR", "no year in birth date"))
            elif year == card.birth_year:
                checks.append(match("V_CCCD_YEAR"))
            else:
                checks.append(mismatch("V_CCCD_YEAR", f"CCCD says {card.birth_year}, date says {year}"))

    if sex is not None:
        stated = _normalise_sex(sex)
        if stated is None:
            checks.append(undetermined("V_CCCD_SEX", f"unrecognised sex {sex!r}"))
        elif stated == card.sex:
            checks.append(match("V_CCCD_SEX"))
        else:
            checks.append(mismatch("V_CCCD_SEX", f"CCCD says {card.sex}, field says {stated}"))

    if birth_registration_place is not None:
        place = parse_address(birth_registration_place).province
        if place is None:
            checks.append(undetermined("V_CCCD_PROVINCE", "province not recognised"))
        elif place == card.province:
            checks.append(match("V_CCCD_PROVINCE"))
        elif place in PROVINCES_POST_2025 and OLD_TO_NEW[card.province] == place:
            checks.append(match("V_CCCD_PROVINCE", f"{card.province} is part of {place} since 2025"))
        else:
            checks.append(mismatch("V_CCCD_PROVINCE", f"CCCD says {card.province}, field says {place}"))
    return checks


def compare_identifiers(a: str, b: str, verifier: str = "V_ID") -> Check:
    """The same identifier stated on two documents: digits must be identical."""
    da, db = re.sub(r"[^0-9]", "", a), re.sub(r"[^0-9]", "", b)
    if not da or not db:
        return undetermined(verifier, "empty identifier")
    if da != db:
        return mismatch(verifier, f"{len(da)} vs {len(db)} digits" if len(da) != len(db) else "digits differ")
    return match(verifier)
