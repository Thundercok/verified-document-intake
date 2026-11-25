import pytest

from document_intake.synth import people
from document_intake.verify import Verdict, check_address_typical, check_name_typical, parse_address, place_tone
from document_intake.verify.lexicon import NAME_SYLLABLES, SURNAMES


@pytest.mark.parametrize(
    "name",
    [
        "TRÂN ĐỨC DŨNG",
        "Đô Minh Đạt",
        "NGUYÊN GIA ĐẠT",
        "Đăng Đức Quý",
        "Võ Hữu Thuy Tuấn",
        "Dỗ Văn An",
        "Nguyèn Văn An",
    ],
)
def test_near_misses_of_typical_names_are_undetermined(name):
    assert check_name_typical(name).verdict is Verdict.UNDETERMINED


@pytest.mark.parametrize(
    "name",
    ["Nguyễn Văn An", "TRẦN THỊ THÚY", "Lê Bảo Trân", "Nguyễn Thảo Nguyên", "Phạm Hải Đăng", "Đỗ Hồng Nhung"],
)
def test_typical_names_match_whatever_the_position_of_a_word(name):
    # "Trân", "Nguyên", "Đăng" are near misses of surnames but ordinary given names.
    assert check_name_typical(name).ok


def test_tone_placement_and_case_are_not_near_misses():
    assert check_name_typical(place_tone("Đặng Kim Thúy Loan", "new").upper()).ok


def test_unknown_words_are_not_judged():
    # No folded neighbour in the lexicon: a rare or foreign name is not a reason to doubt.
    assert check_name_typical("Nguyễn Văn Khỏe").ok
    assert check_name_typical("Smith John").ok
    assert check_name_typical("").verdict is Verdict.UNDETERMINED


def test_every_synthetic_surname_is_in_the_lexicon():
    assert {s.lower() for s in people.SURNAMES} <= SURNAMES
    pool = {w.lower() for w in people.MIDDLE_M + people.MIDDLE_F + people.GIVEN_M + people.GIVEN_F}
    # The lexicon is written independently of the generator; it misses only the odd "Khỏe".
    assert pool - NAME_SYLLABLES == {"khỏe"}


@pytest.mark.parametrize(
    ("addr", "ok"),
    [
        ("Ấp 12, Xã Tân Lập, Huyện Gia Lâm, Tỉnh Trà Vinh", True),
        ("Áp 12, Xã Tân Lập, Huyện Gia Lâm, Tỉnh Trà Vinh", False),
        ("Tô 5, Xã An Phú, Huyện Thanh Trì, Hà Nội", False),
        ("Khu phố 3, Phường An Phú, TP. Hồ Chí Minh", True),
        ("12 Tô Hiến Thành, Phường 13, Quận 10, TP. Hồ Chí Minh", True),  # a street, not "Tổ"
        ("Tô Hiến Thành, Phường 13, Quận 10, TP. Hồ Chí Minh", True),  # no number: not judged
    ],
)
def test_address_unit_word_near_misses(addr, ok):
    assert check_address_typical(parse_address(addr).street).ok is ok
