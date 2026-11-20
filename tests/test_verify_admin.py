import pytest

from document_intake.verify import Verdict, compare_addresses, parse_address, resolve_province
from document_intake.verify.vn_admin import (
    CCCD_PROVINCE_CODES,
    MERGER_2025,
    OLD_TO_NEW,
    PROVINCE_ALIASES,
    PROVINCES_POST_2025,
    PROVINCES_PRE_2025,
)


def test_province_tables_are_consistent():
    assert len(CCCD_PROVINCE_CODES) == 63 == len(PROVINCES_PRE_2025)
    assert all(1 <= int(code) <= 96 for code in CCCD_PROVINCE_CODES)
    assert len(MERGER_2025) == 34
    olds = [o for group in MERGER_2025.values() for o in group]
    assert sorted(olds) == sorted(PROVINCES_PRE_2025)  # every old province mapped exactly once
    assert sum(len(g) == 1 for g in MERGER_2025.values()) == 11
    assert set(OLD_TO_NEW.values()) == PROVINCES_POST_2025
    assert set(PROVINCE_ALIASES.values()) <= PROVINCES_PRE_2025 | PROVINCES_POST_2025


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("TP.HCM", "hồ chí minh"),
        ("TPHCM", "hồ chí minh"),
        ("Thành phố Hồ Chí Minh", "hồ chí minh"),
        ("Sài Gòn", "hồ chí minh"),
        ("Thủ đô Hà Nội", "hà nội"),
        ("Tỉnh Hoà Bình", "hòa bình"),  # new-style tone placement
        ("Đăk Lăk", "đắk lắk"),
        ("Tỉnh Bà Rịa - Vũng Tàu", "bà rịa vũng tàu"),
        ("Thừa Thiên - Huế", "thừa thiên huế"),
        ("Thành phố Huế", "huế"),
        ("Hà Năm", "hà nam"),  # tone error resolved through the closed vocabulary
        ("Atlantis", None),
    ],
)
def test_resolve_province(text, name):
    assert resolve_province(text) == name


def test_parse_address_pre_2025():
    a = parse_address("Số 12 đường Nguyễn Trãi, P.5, Q.3, TP.HCM")
    assert (a.street, a.commune, a.district, a.province) == ("12 nguyễn trãi", "5", "3", "hồ chí minh")
    assert a.era == "pre2025" and a.new_province == "hồ chí minh"
    b = parse_address("Xã An Phú, Thị xã Thuận An, Tỉnh Bình Dương")
    assert (b.commune, b.district, b.era, b.new_province) == ("an phú", "thuận an", "pre2025", "hồ chí minh")


def test_parse_address_post_2025_and_unclassified():
    a = parse_address("Thôn 3, Xã Tân Lập, Tỉnh Phú Thọ")
    assert (a.street, a.commune, a.district, a.era) == ("thôn 3", "tân lập", None, "post2025")
    # An unprefixed component where a district would be stops classification: no commune guessed.
    b = parse_address("Phường 7, Thủ Đức, TP HCM")
    assert b.commune is None and b.province == "hồ chí minh"


def test_compare_addresses_full_match_across_spellings():
    c = compare_addresses(
        "Số 12 Nguyễn Trãi, Phường 05, Quận 3, TP. Hồ Chí Minh", "12 đường Nguyễn Trãi, P.5, Q3, TPHCM"
    )
    assert c.verdict is Verdict.MATCH and c.detail == "full"


def test_compare_addresses_across_eras_is_undetermined_not_mismatch():
    c = compare_addresses("Xã An Phú, Thị xã Thuận An, Tỉnh Bình Dương", "Phường An Phú, Thành phố Hồ Chí Minh")
    assert c.verdict is Verdict.UNDETERMINED and c.detail.startswith("province")


@pytest.mark.parametrize(
    ("a", "b", "detail_start"),
    [
        ("Phường 5, Quận 3, TP HCM", "Phường 5, Quận 3, Hà Nội", "none"),
        ("Xã A, Huyện B, Tỉnh Bình Dương", "Xã A, Huyện B, Tỉnh Bà Rịa - Vũng Tàu", "none: pre-2025"),
        ("Phường 5, Quận 3, TP HCM", "Phường 5, Quận 10, TP HCM", "province: district"),
        ("Phường 5, Quận 3, TP HCM", "Phường 6, Quận 3, TP HCM", "province: commune"),
        ("12 Nguyễn Trãi, Phường 5, Quận 3, TP HCM", "21 Nguyễn Trãi, Phường 5, Quận 3, TP HCM", "commune: street"),
    ],
)
def test_compare_addresses_mismatch_levels(a, b, detail_start):
    c = compare_addresses(a, b)
    assert c.verdict is Verdict.MISMATCH and c.detail.startswith(detail_start)


def test_compare_addresses_missing_parts_are_undetermined():
    assert compare_addresses("Phường 5, TP HCM", "Phường 5, Quận 3, TP HCM").verdict is Verdict.UNDETERMINED
    assert compare_addresses("Phường Bàn Cờ, TP HCM", "TP HCM").verdict is Verdict.UNDETERMINED
    assert compare_addresses("Atlantis", "TP HCM").verdict is Verdict.UNDETERMINED
