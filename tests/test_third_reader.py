"""Rule G of v10 (audits/real_scans/third_reader.py): parsing Gemma's read of the number line."""

import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "audits" / "real_scans" / "third_reader.py"
spec = importlib.util.spec_from_file_location("third_reader", PATH)
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


@pytest.mark.parametrize(
    ("text", "want"),
    [
        ("Số: 2615/QĐ-TTg", 2615),
        ("2491QĐ-TTg", 2491),  # no slash
        ("Số:-653/TB-VPC", 653),
        ("5 6/2025/TT-BCT", 56),
        ("Số: 14-71 /QĐ-TTg", 1471),
        ("3†3/QĐ-TTg", 373),
        ("Số: ‡‡3/QĐ-TTg", 773),
        ("5T/QĐ-TTg", 57),
        ("H01/QĐ-TTg", 401),
        ("Số:gg/2026/TT-BTC", 99),
        ("Số:", None),
        ("Số: $\\text{Số: } \\text{Q} \\text{o} \\text{o} /2025/\\text{TT", None),  # batch 9, id 104
    ],
)
def test_lead_number(text, want):
    assert G.lead_number(text) == want


def test_third_ok():
    assert G.third_ok("02/2025/TT-BTTTT", "Số: 2/2025/TT-BTTTT")  # compared as integers
    assert not G.third_ok("62/2025/TT-BTTTT", "620/2025/TT-BTTTT")
    assert not G.third_ok("249/QĐ-TTg", "2491QĐ-TTg")  # batch 7, id 366: caught
    assert G.third_ok("2645/QĐ-TTg", "Số:2645/QĐ-TTg")  # batch 7, id 192: Gemma shares the misread
    assert not G.third_ok("62/2025/TT-BTTTT", None)


def test_numline_box():
    obs = [
        {"text": "BỘ TÀI CHÍNH", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.04},
        {"text": "Số: 63 /2026/TT-BTC", "x": 0.08, "y": 0.4, "w": 0.3, "h": 0.05},
        {"text": "Hà Nội, ngày 1 tháng 2 năm 2026", "x": 0.5, "y": 0.4, "w": 0.4, "h": 0.05},
    ]
    x0, y0, x1, y1 = G.numline_box(obs)
    assert x0 == pytest.approx(0.05) and x1 == pytest.approx(0.50)
    assert y0 == pytest.approx(0.36) and y1 == pytest.approx(0.49)
    assert G.numline_box([{"text": "QUYẾT ĐỊNH", "x": 0.3, "y": 0.5, "w": 0.3, "h": 0.05}]) is None
