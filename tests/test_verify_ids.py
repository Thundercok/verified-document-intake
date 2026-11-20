# All identifiers below are synthetic. Never put a real CCCD or tax code in this repo.
from datetime import date

import pytest

from document_intake.verify import (
    Verdict,
    check_cccd_consistency,
    check_cccd_format,
    check_mst,
    mst_check_digit,
    parse_cccd,
    parse_mst,
)

SYNTH = "079203000001"  # 079 = TP HCM, 2 = 2000s male, 03 = 2003


def test_parse_cccd_fields():
    card = parse_cccd(SYNTH)
    assert (card.province, card.sex, card.birth_year) == ("hồ chí minh", "nam", 2003)
    assert parse_cccd("001 1 85 000002").sex == "nữ"  # 1 = 1900s female
    assert parse_cccd("001185000002").birth_year == 1985


@pytest.mark.parametrize(
    "bad",
    ["07920300000", "0792030000012", "07920300000A", "003203000001", "099203000001"],
)
def test_parse_cccd_rejects_bad_structure(bad):
    with pytest.raises(ValueError):
        parse_cccd(bad)


def test_parse_cccd_rejects_future_birth_year():
    with pytest.raises(ValueError, match="future"):
        parse_cccd("079230000001", today=date(2026, 11, 20))  # 2030


def test_check_cccd_format_verdicts():
    assert check_cccd_format(SYNTH).verdict is Verdict.MATCH
    assert check_cccd_format("003203000001").verdict is Verdict.MISMATCH
    assert check_cccd_format("  ").verdict is Verdict.UNDETERMINED


def test_cccd_consistency_all_agree():
    checks = check_cccd_consistency(
        SYNTH, birth_date="14/02/2003", sex="Nam", birth_registration_place="Quận 1, TP. Hồ Chí Minh"
    )
    assert [c.verdict for c in checks] == [Verdict.MATCH] * 4


def test_cccd_consistency_detects_each_disagreement():
    checks = {
        c.verifier: c
        for c in check_cccd_consistency(SYNTH, birth_date="14/02/2004", sex="Nữ", birth_registration_place="Hà Nội")
    }
    assert checks["V_CCCD_YEAR"].verdict is Verdict.MISMATCH
    assert checks["V_CCCD_SEX"].verdict is Verdict.MISMATCH
    assert checks["V_CCCD_PROVINCE"].verdict is Verdict.MISMATCH


def test_cccd_province_survives_2025_merger():
    # 074 = Bình Dương, merged into TP HCM; a post-2025 form may write the new province.
    checks = check_cccd_consistency("074203000001", birth_registration_place="Thành phố Hồ Chí Minh")
    assert checks[-1].verdict is Verdict.MATCH
    assert "since 2025" in checks[-1].detail
    # ...but the reverse is not implied: an HCM code never means Bình Dương.
    checks = check_cccd_consistency(SYNTH, birth_registration_place="Tỉnh Bình Dương")
    assert checks[-1].verdict is Verdict.MISMATCH


def test_cccd_consistency_unknown_fields_are_undetermined():
    checks = check_cccd_consistency(SYNTH, birth_date="năm 2003", sex="?", birth_registration_place="Atlantis")
    by = {c.verifier: c.verdict for c in checks}
    assert by["V_CCCD_YEAR"] is Verdict.MATCH
    assert by["V_CCCD_SEX"] is Verdict.UNDETERMINED
    assert by["V_CCCD_PROVINCE"] is Verdict.UNDETERMINED


def test_mst_check_digit_known_vector():
    # 0*31 + 1*29 + 0*23 + 0*19 + 2*17 + 3*13 + 3*7 + 4*5 + 8*3 = 167; (10 - 167 % 11) % 11 = 8
    assert mst_check_digit("010023348") == 8
    assert parse_mst("0100233488") == "base10"


def test_mst_every_single_digit_substitution_of_check_digit_is_caught():
    for d in "012345679":
        assert check_mst("010023348" + d).verdict is Verdict.MISMATCH


def test_mst_branch_and_personal_forms():
    assert parse_mst("0314409058-002") == "branch13"
    assert parse_mst("0314409058002") == "branch13"
    assert parse_mst(SYNTH) == "personal12"
    with pytest.raises(ValueError, match="000"):
        parse_mst("0314409058-000")
    with pytest.raises(ValueError):
        parse_mst("0314409059-002")  # bad check digit in the base


def test_mst_remainder_ten_admits_no_check_digit():
    # Find a 9-digit prefix whose weighted sum is 0 mod 11: no 10th digit can be valid.
    prefix = next(
        f"{n:09d}"
        for n in range(10**9)
        if sum(w * int(c) for w, c in zip((31, 29, 23, 19, 17, 13, 7, 5, 3), f"{n:09d}", strict=True)) % 11 == 0
        and n > 0
    )
    assert mst_check_digit(prefix) is None
    assert all(check_mst(prefix + d).verdict is Verdict.MISMATCH for d in "0123456789")
