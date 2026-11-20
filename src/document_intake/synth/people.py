"""Synthetic people, addresses and invoices. Every value is generated; none is a real record.

A `Person` is internally consistent the way real documents are: the CCCD prefix encodes the
birth-registration province, sex and birth year, and the person has one residence written two
ways (the pre-2025 four-level address on an older card, the post-2025 three-level address on a
new form). Commune names after the reform are drawn from a separate pool, because without a
gazetteer the new name of a merged commune is not derivable from the old one.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import date, timedelta

from ..verify.mst import mst_check_digit
from ..verify.vn_admin import CCCD_PROVINCE_CODES, OLD_TO_NEW

SURNAMES = ("Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô")
MIDDLE_M = ("Văn", "Hữu", "Đức", "Minh", "Quốc", "Thanh", "Xuân", "Công", "Gia")
MIDDLE_F = ("Thị", "Ngọc", "Thu", "Thanh", "Minh", "Kim", "Mỹ", "Bảo")
# Open oa/oe/uy rhymes (Hòa, Thúy, Khỏe...) are over-represented on purpose: they are the names
# whose tone placement varies between documents.
GIVEN_M = ("An", "Bình", "Dũng", "Hùng", "Tuấn", "Hòa", "Thụy", "Khoa", "Toàn", "Huy", "Quý", "Đạt", "Lộc", "Khỏe")
GIVEN_F = ("Lan", "Hương", "Thúy", "Thủy", "Hoa", "Loan", "Quỳnh", "Uyên", "Tuyết", "Phượng", "Hòa", "Huệ", "Ngọc")
STREETS = (
    "Nguyễn Trãi",
    "Lê Lợi",
    "Trần Hưng Đạo",
    "Hai Bà Trưng",
    "Lý Thường Kiệt",
    "Phan Đình Phùng",
    "Điện Biên Phủ",
    "Võ Văn Tần",
    "Hoàng Diệu",
    "Quang Trung",
)
VILLAGES = ("Thôn", "Ấp", "Tổ", "Khu phố")
COMMUNES_OLD = ("An Phú", "Tân Lập", "Hòa Bình", "Bình An", "Phú Hòa", "Tân Thành", "Long Hưng", "Thạnh Mỹ")
COMMUNES_NEW = ("Bến Thành", "Hòa Khánh", "Thuận Giao", "Phú Lợi", "Tân Hiệp", "Long Thủy", "Đông Hòa", "Vĩnh Lộc")
DISTRICTS = ("Bình Chánh", "Thuận An", "Gia Lâm", "Thanh Trì", "Châu Thành", "Phú Giáo", "Long Thành", "Hòa Vang")
CITIES = frozenset({"hà nội", "hồ chí minh", "hải phòng", "đà nẵng", "cần thơ", "huế"})

_CODE_OF = {name: code for code, name in CCCD_PROVINCE_CODES.items()}


@dataclass(frozen=True)
class OldAddress:
    street: str  # "12 Nguyễn Trãi" or "Thôn 3"
    commune_kind: str  # phường | xã | thị trấn
    commune: str  # "5" or "An Phú"
    district_kind: str  # quận | huyện | thị xã | thành phố
    district: str
    province: str  # canonical pre-2025 name


@dataclass(frozen=True)
class NewAddress:
    street: str
    commune_kind: str  # phường | xã
    commune: str
    province: str  # canonical post-2025 name


@dataclass(frozen=True)
class Person:
    name: str
    sex: str  # "nam" | "nữ"
    dob: date
    birth_province: str  # pre-2025, place of birth registration
    cccd_tail: str  # random last six digits
    old_address: OldAddress
    new_address: NewAddress

    @property
    def cccd(self) -> str:
        return make_cccd(self.birth_province, self.sex, self.dob.year, self.cccd_tail)


def make_cccd(province: str, sex: str, year: int, tail: str) -> str:
    century = (year - 1900) // 100
    digit = century * 2 + (1 if sex == "nữ" else 0)
    return f"{_CODE_OF[province]}{digit}{year % 100:02d}{tail}"


def _old_address(rng: random.Random, province: str) -> OldAddress:
    urban = province in CITIES or rng.random() < 0.4
    if urban:
        street = f"{rng.randint(1, 299)} {rng.choice(STREETS)}"
        if rng.random() < 0.5:
            commune_kind, commune = "phường", str(rng.randint(1, 15))
            district_kind, district = "quận", str(rng.randint(1, 12))
        else:
            commune_kind, commune = "phường", rng.choice(COMMUNES_OLD)
            district_kind, district = rng.choice(("thành phố", "thị xã")), rng.choice(DISTRICTS)
    else:
        street = f"{rng.choice(VILLAGES)} {rng.randint(1, 12)}"
        commune_kind, commune = rng.choice((("xã", rng.choice(COMMUNES_OLD)), ("thị trấn", rng.choice(COMMUNES_OLD))))
        district_kind, district = "huyện", rng.choice(DISTRICTS)
    return OldAddress(street, commune_kind, commune, district_kind, district, province)


def _new_address(rng: random.Random, old: OldAddress) -> NewAddress:
    kind = "xã" if old.commune_kind in ("xã", "thị trấn") else "phường"
    keeps_name = not old.commune.isdigit() and rng.random() < 0.3
    return NewAddress(
        old.street, kind, old.commune if keeps_name else rng.choice(COMMUNES_NEW), OLD_TO_NEW[old.province]
    )


def make_person(rng: random.Random) -> Person:
    sex = rng.choice(("nam", "nữ"))
    middle, given = (MIDDLE_M, GIVEN_M) if sex == "nam" else (MIDDLE_F, GIVEN_F)
    name = f"{rng.choice(SURNAMES)} {rng.choice(middle)} {rng.choice(given)}"
    if rng.random() < 0.3:
        name = f"{name.rsplit(' ', 1)[0]} {rng.choice(given)} {rng.choice(given)}"
    dob = date(1950, 1, 1) + timedelta(days=rng.randrange((date(2008, 12, 31) - date(1950, 1, 1)).days))
    birth_province = rng.choice(sorted(CCCD_PROVINCE_CODES.values()))
    residence = birth_province if rng.random() < 0.6 else rng.choice(sorted(CCCD_PROVINCE_CODES.values()))
    old = _old_address(rng, residence)
    return Person(name, sex, dob, birth_province, f"{rng.randrange(10**6):06d}", old, _new_address(rng, old))


def with_changes(person: Person, **changes) -> Person:
    """A different but internally consistent person (the CCCD follows dob/sex/province)."""
    return replace(person, **changes)


def make_mst(rng: random.Random, branch: bool = False) -> str:
    """A structurally valid organisation tax code (never a real one by intent; not looked up)."""
    while True:
        first9 = f"{rng.randint(1, 99):02d}{rng.randrange(10**7):07d}"
        check = mst_check_digit(first9)
        if check is not None:
            base = f"{first9}{check}"
            return f"{base}-{rng.randint(1, 999):03d}" if branch else base


def make_amount(rng: random.Random) -> int:
    """Invoice totals: mostly round to 1,000 or 10,000 VND, spread over 10^4 to 10^10."""
    magnitude = rng.choice((10**4, 10**5, 10**6, 10**7, 10**8, 10**9))
    unit = rng.choice((1000, 1000, 10_000))
    return max(unit, round(rng.randint(magnitude, magnitude * 10) / unit) * unit)
