import pytest

from document_intake.verify import Verdict, check_amount, parse_amount_digits, parse_number_words


@pytest.mark.parametrize(
    ("words", "value"),
    [
        ("không", 0),
        ("năm", 5),
        ("mười", 10),
        ("mười lăm", 15),
        ("mười tư", 14),
        ("hai mươi", 20),
        ("hai mươi mốt", 21),
        ("hai mươi một", 21),
        ("ba mươi tư", 34),
        ("chín mươi nhăm", 95),
        ("một trăm", 100),
        ("một trăm linh năm", 105),
        ("một trăm lẻ tư", 104),
        ("một trăm mười", 110),
        ("chín trăm chín mươi chín", 999),
        ("một nghìn", 1000),
        ("một ngàn không trăm linh năm", 1005),
        ("một nghìn linh năm", 1005),
        ("hai nghìn không trăm mười tám", 2018),
        ("một nghìn chín trăm tám mươi lăm", 1985),
        ("một triệu năm nghìn", 1_005_000),
        ("một triệu hai trăm ba mươi nghìn đồng", 1_230_000),
        ("Một triệu không trăm năm mươi nghìn đồng chẵn./.", 1_050_000),
        ("mười hai tỷ", 12_000_000_000),
        ("một tỉ hai trăm triệu", 1_200_000_000),
        ("một nghìn tỷ", 10**12),
        ("MƯỜI LĂM TRIỆU ĐỒNG", 15_000_000),
        ("năm mươi triệu Việt Nam đồng", 50_000_000),
    ],
)
def test_parse_number_words(words, value):
    assert parse_number_words(words) == value


@pytest.mark.parametrize(
    "words",
    [
        "",
        "mười năm",  # five after mười must be lăm
        "hai mươi năm",
        "một trăm năm",  # colloquial 150, formally ambiguous
        "một nghìn năm",  # colloquial 1500
        "mười mốt",
        "một mươi",
        "không trăm hai mươi",  # leading không trăm
        "nghìn",
        "không nghìn",
        "một nghìn triệu",
        "trăm",
        "một trăm linh",
        "hai triệu ba triệu",
        "một hai",
        "tám nghìn đô",
    ],
)
def test_parse_number_words_rejects(words):
    with pytest.raises(ValueError):
        parse_number_words(words)


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1.230.000", 1_230_000),
        ("1,230,000", 1_230_000),
        ("1 230 000", 1_230_000),
        ("1230000", 1_230_000),
        ("1.230.000 đồng", 1_230_000),
        ("1.230.000đ", 1_230_000),
        ("1.230.000,00", 1_230_000),
        ("500 VNĐ", 500),
    ],
)
def test_parse_amount_digits(text, value):
    assert parse_amount_digits(text) == value


@pytest.mark.parametrize("text", ["1.5", "1.23.000", "1.230,000", "abc", "1.230.000,50"])
def test_parse_amount_digits_rejects(text):
    with pytest.raises(ValueError):
        parse_amount_digits(text)


def test_check_amount_verdicts():
    assert check_amount("1.230.000", "Một triệu hai trăm ba mươi nghìn đồng").verdict is Verdict.MATCH
    # A dropped zero in the digits, the typical OCR error.
    c = check_amount("123.000", "Một triệu hai trăm ba mươi nghìn đồng")
    assert c.verdict is Verdict.MISMATCH and "digits 123000" in c.detail
    # Grammar violation in the words is a detected error, not "no evidence".
    assert check_amount("15", "mười năm").verdict is Verdict.MISMATCH
    assert check_amount("", "mười lăm").verdict is Verdict.UNDETERMINED


def test_number_to_words_examples():
    from document_intake.verify import number_to_words

    assert number_to_words(0) == "không"
    assert number_to_words(21) == "hai mươi mốt"
    assert number_to_words(105) == "một trăm linh năm"
    assert number_to_words(1_005_000) == "một triệu không trăm linh năm nghìn"
    assert number_to_words(1_000_005) == "một triệu không trăm linh năm"
    assert number_to_words(2018, thousand="ngàn") == "hai ngàn không trăm mười tám"
    assert number_to_words(95, five="nhăm") == "chín mươi nhăm"
    with pytest.raises(ValueError):
        number_to_words(-1)


def test_number_to_words_round_trips_through_the_parser():
    import random

    from document_intake.verify import number_to_words

    rng = random.Random(0)
    values = [*range(20001), *(rng.randrange(10**15) for _ in range(2000))]
    variants = [{}, {"thousand": "ngàn", "linh": "lẻ", "one_after_tens": "một", "four_after_tens": "bốn"}]
    for kwargs in variants:
        for n in values:
            assert parse_number_words(number_to_words(n, **kwargs)) == n
