"""Meaning-preserving renderings: the same fact written the way different documents write it.

A verifier that raises an alarm on these is producing false alarms, not catching errors: CCCD
prints names in capitals, a birth certificate writes the date in words, an older card carries the
pre-2025 four-level address, and forms abbreviate (P.5, Q.3, TP.HCM) or use either tone
placement (Hòa / Hoà).
"""

from __future__ import annotations

import random
import unicodedata
from datetime import date

from ..verify.number_words import number_to_words
from ..verify.text import place_tone
from .people import CITIES, NewAddress, OldAddress

_SPECIAL_TITLES = {"bà rịa vũng tàu": "Bà Rịa - Vũng Tàu", "hồ chí minh": "Hồ Chí Minh"}


def title(name: str) -> str:
    return _SPECIAL_TITLES.get(name) or " ".join(w[:1].upper() + w[1:] for w in name.split())


def render_name(name: str, rng: random.Random, upper: bool | None = None) -> str:
    text = place_tone(name, rng.choice(("old", "new")))
    if upper if upper is not None else rng.random() < 0.4:
        text = text.upper()
    if rng.random() < 0.1:
        text = unicodedata.normalize("NFD", text)
    return text


DATE_STYLES = ("dmy", "dmy_short", "labelled", "words")


def render_date(d: date, rng: random.Random, style: str | None = None) -> str:
    style = style or rng.choice(DATE_STYLES)
    if style == "dmy":
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    if style == "dmy_short":
        return f"{d.day}/{d.month}/{d.year}"
    if style == "labelled":
        return f"ngày {d.day:02d} tháng {d.month:02d} năm {d.year}"
    day = number_to_words(d.day)
    if d.day <= 10 and rng.random() < 0.5:
        day = f"mồng {day}"
    month = "tư" if d.month == 4 and rng.random() < 0.5 else number_to_words(d.month)
    year = number_to_words(d.year, thousand=rng.choice(("nghìn", "ngàn")))
    return f"ngày {day} tháng {month} năm {year}"


def _province(name: str, rng: random.Random, abbreviate: bool) -> str:
    if abbreviate:
        if name == "hồ chí minh":
            return rng.choice(("TP.HCM", "TP. Hồ Chí Minh", "TPHCM"))
        return f"TP. {title(name)}" if name in CITIES and rng.random() < 0.5 else title(name)
    return f"{'Thành phố' if name in CITIES else 'Tỉnh'} {title(name)}"


def _street(street: str, rng: random.Random) -> str:
    if not street[0].isdigit():
        return street
    number, rest = street.split(" ", 1)
    return rng.choice((street, f"Số {street}", f"Số {number} đường {rest}"))


def _commune(kind: str, name: str, rng: random.Random, abbreviate: bool) -> str:
    if name.isdigit() and rng.random() < 0.3:
        name = f"{int(name):02d}"
    if abbreviate:
        short = {"phường": "P.", "thị trấn": "TT.", "xã": rng.choice(("Xã ", "X."))}[kind]
        return f"{short}{name}" if rng.random() < 0.5 or short.endswith(" ") else f"{short} {name}"
    return f"{kind.capitalize()} {name}"


def _district(kind: str, name: str, rng: random.Random, abbreviate: bool) -> str:
    if abbreviate:
        short = {"quận": "Q.", "huyện": "H.", "thị xã": "TX.", "thành phố": "TP."}[kind]
        return f"{short}{name}" if name.isdigit() and rng.random() < 0.5 else f"{short} {name}"
    return f"{kind.capitalize()} {name}"


def render_old_address(a: OldAddress, rng: random.Random, abbreviate: bool = False) -> str:
    return ", ".join(
        (
            _street(a.street, rng),
            _commune(a.commune_kind, a.commune, rng, abbreviate),
            _district(a.district_kind, a.district, rng, abbreviate),
            _province(a.province, rng, abbreviate),
        )
    )


def render_new_address(a: NewAddress, rng: random.Random, abbreviate: bool = False) -> str:
    return ", ".join(
        (
            _street(a.street, rng),
            _commune(a.commune_kind, a.commune, rng, abbreviate),
            _province(a.province, rng, abbreviate),
        )
    )


def render_place(province_old: str, province_new: str, rng: random.Random) -> str:
    """Place of birth registration, at province level, in either era."""
    return _province(province_old if rng.random() < 0.5 else province_new, rng, rng.random() < 0.3)


def render_sex(sex: str, rng: random.Random) -> str:
    text = sex.capitalize()
    return text.upper() if rng.random() < 0.3 else text


def render_cccd(number: str, rng: random.Random) -> str:
    return f"{number[:3]} {number[3:6]} {number[6:9]} {number[9:]}" if rng.random() < 0.3 else number


def render_amount_digits(n: int, rng: random.Random) -> str:
    text = f"{n:,}".replace(",", ".")
    return text + rng.choice(("", "", " đồng", "đ"))


def render_amount_words(n: int, rng: random.Random) -> str:
    words = number_to_words(
        n,
        thousand=rng.choice(("nghìn", "ngàn")),
        linh=rng.choice(("linh", "lẻ")),
        one_after_tens=rng.choice(("mốt", "một")),
        four_after_tens=rng.choice(("tư", "bốn")),
        five=rng.choice(("lăm", "lăm", "nhăm")),
    )
    text = words[0].upper() + words[1:] + " đồng"
    return text + rng.choice(("", " chẵn", "./.", " chẵn./."))
