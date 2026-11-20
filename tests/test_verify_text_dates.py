import unicodedata

import pytest

from document_intake.verify import PartialDate, Verdict, compare_dates, compare_names, parse_date, text_key


def test_names_equal_across_case_unicode_form_and_tone_placement():
    nfd = unicodedata.normalize("NFD", "Nguyễn Thị Thúy Hòa")
    assert compare_names("NGUYỄN THỊ THUÝ HOÀ", nfd).verdict is Verdict.MATCH
    assert compare_names("  Nguyễn   Văn  An ", "nguyễn văn an").verdict is Verdict.MATCH
    assert text_key("khỏe") == text_key("khoẻ")


def test_names_diacritic_only_difference_is_flagged_not_accepted():
    c = compare_names("Nguyễn Thị Thủy", "Nguyễn Thị Thùy")
    assert c.verdict is Verdict.MISMATCH and "diacritics" in c.detail
    c = compare_names("Đặng Văn An", "Dặng Văn An")  # đ vs d: also only a diacritic
    assert c.verdict is Verdict.MISMATCH and "diacritics" in c.detail


def test_names_other_outcomes():
    assert compare_names("Nguyễn Văn An", "Nguyễn An").detail == "3 vs 2 syllables"
    assert compare_names("Trần Văn An", "Lê Văn An").verdict is Verdict.MISMATCH
    assert compare_names("", "Lê Văn An").verdict is Verdict.UNDETERMINED
    assert compare_names("Ðặng An", "Đặng An").verdict is Verdict.MATCH  # eth OCR substitute


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("15/03/2018", PartialDate(2018, 3, 15)),
        ("5-3-2018", PartialDate(2018, 3, 5)),
        ("15.03.2018", PartialDate(2018, 3, 15)),
        ("03/2018", PartialDate(2018, 3)),
        ("2018", PartialDate(2018)),
        ("ngày 15 tháng 3 năm 2018", PartialDate(2018, 3, 15)),
        ("Hà Nội, ngày 15 tháng 03 năm 2018", PartialDate(2018, 3, 15)),
        ("ngày mồng 5 tháng 3 năm 2018", PartialDate(2018, 3, 5)),
        ("ngày mười lăm tháng ba năm hai nghìn không trăm mười tám", PartialDate(2018, 3, 15)),
        ("ngày năm tháng năm năm một nghìn chín trăm chín mươi lăm", PartialDate(1995, 5, 5)),
        ("ngày ba mươi mốt tháng mười hai năm hai nghìn", PartialDate(2000, 12, 31)),
        ("ngày ..... tháng ..... năm 2018", PartialDate(2018)),
        ("ngày 15 tháng 3 năm 20 18", PartialDate(2018, 3, 15)),
        ("năm 2003", PartialDate(2003)),
    ],
)
def test_parse_date(text, expected):
    assert parse_date(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "31/02/2018",
        "29/02/2019",
        "15/13/2018",
        "ngày 15 tháng 3 năm 18",
        "hôm qua",
        "ngày 15",
        "ngày 32 tháng 1 năm 2000",
    ],
)
def test_parse_date_rejects(text):
    with pytest.raises(ValueError):
        parse_date(text)


def test_compare_dates():
    assert compare_dates("15/03/2018", "ngày mười lăm tháng ba năm hai nghìn không trăm mười tám").ok
    assert compare_dates("05/03/2018", "03/05/2018").detail == "day/month swapped"
    assert compare_dates("15/03/2018", "15/03/2019").detail == "differs in year"
    c = compare_dates("15/03/2018", "2018")
    assert c.verdict is Verdict.UNDETERMINED and "year only" in c.detail
    assert compare_dates("15/03/2018", "31/02/2018").verdict is Verdict.MISMATCH
    assert str(PartialDate(2018, None, None)) == "../../2018"
