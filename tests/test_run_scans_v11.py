"""Rules of v11 (audits/real_scans/run_scans.py), on reads quoted from batch 10's rejections."""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "audits" / "real_scans"
sys.path.insert(0, str(DIR))
spec = importlib.util.spec_from_file_location("run_scans", DIR / "run_scans.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def test_rule_s_capital_and_comma_below():
    assert R.read_numbers4("Hạnh phúc 4-o- SỐ: 1324/QĐ-TTg Hà Nội, ngày 02") == []  # v4-v10
    assert R.read_numbers4("Hạnh phúc 4-o- SỐ: 1324/QĐ-TTg Hà Nội, ngày 02", R.SO11_RE) == ["1324/QĐ-TTg"]
    assert R.read_numbers4("phúc Șố: 146/2024/NĐ-CP Hà Nội", R.SO11_RE) == ["146/2024/NĐ-CP"]
    assert R.read_numbers4("phúc Șố:_146/2024/NĐ-CP Hà Nội", R.SO11_RE) == []  # batch 10, id 1011: still lost


def test_rule_y_types_compared_whole():
    d = (29, 10, 2024)
    assert not R.checks_pass6("884/TTg-CN", d)  # "TTg" starts with "TT"
    assert R.checks_pass11("884/TTg-CN", d)
    assert not R.checks_pass11("22/TT-BCT", d)  # a circular still needs its year
    assert not R.checks_pass11("51/QH15", d)
    assert R.checks_pass11("1257/NQ-UBTVQH15", d)


def test_rule_e_two_digit_day():
    text = "Số: 16/2024/NQ-HĐND Ninh Bình, ngày 30 tháng 10 năm 2024 Thời gian ký: 18.11.2024 10:21"
    assert not R.emblem_ok(text, (30, 10, 2024))  # 19 days
    assert R.emblem_ok11(text, (30, 10, 2024))
    short = "Số: 6/2026/VBHN-BTC Hà Nội, ngày 2 tháng 9 năm 2026 Thời gian ký: 22.09.2026 10:21"
    assert not R.emblem_ok11(short, (2, 9, 2026))  # "21" read as 2: the window stays 14 days


def test_rule_p_standing_committee():
    t = "khóa XV thông qua tại phiên họp ngày 24 tháng 10 năm 2024. Nơi nhận:"
    assert R.passed_date(t) is None
    assert R.passed_date11(t) == (24, 10, 2024)
    assert R.passed_date11("Quốc hội thông qua ngày 29 tháng 11 năm 2024.") == (29, 11, 2024)


def test_rule_f_damaged_date_line():
    f = R.read_date_f
    assert f("Hà Nội, ngày 0 5 tháng 11 năm 2024 THÔNG TƯ") == (5, 11, 2024)
    assert f("Hà Nội, ngày 07 tháng1 1 năm 2024") == (7, 11, 2024)
    assert f("Hà Nội, ngày 15 tháng |1 năm 2024") == (15, 11, 2024)
    assert f("Hà Nội, ngày// tháng 12 năm 2024") == (11, 12, 2024)
    assert f("Hà Nội, ngày 27 tháng 12 năm 202:4m") is None  # only spaces may split the year
    assert f("Hà Nội, ngày 24 thán đOR TRN") is None
    assert f("Hà Nội, ngày25 tháng Knăm 2024") is None  # a letter for the month: no read


def test_read_v11_fuzzy_needs_qwen_to_agree():
    text = "Số: 31 /2024/TT-BYT Hà Nội, ngày 07 tháng1 1 năm 2024 THÔNG TƯ"
    assert R.read_v11(text, "31/2024/TT-BYT\n07/11/2024", None, None, None, None)[2] == "fuzzy"
    assert R.read_v11(text, "31/2024/TT-BYT\n07/01/2024", None, None, None, None)[0] is None


def test_confirm11_needs_gemma_for_reads_rule_g_removed():
    """Batch 11: a v11 read with no Gemma read was vetoed by rule G and slipped past the guard."""
    import pytest

    row = {
        "id": 2,
        "v3": {"qwen": "x"},
        "v9": {"auth": False, "passed": False, "num": None, "where": "page1"},
        "v10": {"crop": True, "gemma_read": False},
        "v11": {"passed": False, "num": None, "veto": True, "veto_num": "1229/QĐ-TTg", "where": "page1"},
    }
    with pytest.raises(SystemExit, match="no Gemma read"):
        R.confirm11([row])
