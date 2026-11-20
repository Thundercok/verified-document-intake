import random

from document_intake.synth import corrupt, make_amount, make_mst, make_person
from document_intake.synth.noise import OPS
from document_intake.synth.render import (
    DATE_STYLES,
    render_amount_digits,
    render_amount_words,
    render_date,
    render_name,
    render_new_address,
    render_old_address,
    render_place,
    render_sex,
)
from document_intake.verify import (
    check_amount,
    check_cccd_consistency,
    check_mst,
    compare_addresses,
    compare_dates,
    compare_names,
    text_key,
)
from document_intake.verify.vn_admin import OLD_TO_NEW


def test_generation_is_deterministic():
    assert make_person(random.Random(5)) == make_person(random.Random(5))
    assert make_mst(random.Random(5)) == make_mst(random.Random(5))


def test_people_are_internally_consistent():
    rng = random.Random(1)
    for _ in range(500):
        p = make_person(rng)
        place = render_place(p.birth_province, OLD_TO_NEW[p.birth_province], rng)
        checks = check_cccd_consistency(
            p.cccd, birth_date=render_date(p.dob, rng), sex=render_sex(p.sex, rng), birth_registration_place=place
        )
        assert all(c.ok for c in checks), (p, checks)
        assert p.new_address.province == OLD_TO_NEW[p.old_address.province]


def test_renderings_preserve_meaning():
    """Clean renderings must never raise an alarm: that would be a false alarm, not detection."""
    rng = random.Random(2)
    for _ in range(500):
        p = make_person(rng)
        assert compare_names(render_name(p.name, rng, upper=True), render_name(p.name, rng)).ok
        for style in DATE_STYLES:
            assert compare_dates(render_date(p.dob, rng, "dmy"), render_date(p.dob, rng, style)).ok
        old_a, old_b = render_old_address(p.old_address, rng), render_old_address(p.old_address, rng, True)
        assert compare_addresses(old_a, old_b).ok, (old_a, old_b)
        new_a, new_b = render_new_address(p.new_address, rng), render_new_address(p.new_address, rng, True)
        assert compare_addresses(new_a, new_b).ok, (new_a, new_b)
        n = make_amount(rng)
        assert check_amount(render_amount_digits(n, rng), render_amount_words(n, rng)).ok
        assert check_mst(make_mst(rng, branch=rng.random() < 0.5)).ok


def test_corrupt_changes_text_and_names_the_edit():
    rng = random.Random(3)
    names = {op.__name__ for ops in OPS.values() for op in ops}
    for kind, text in (("text", "Nguyễn Thị Thúy"), ("digits", "079203000001"), ("words", "mười lăm nghìn")):
        for _ in range(50):
            c = corrupt(text, rng, kind)
            assert c is not None and c.text != text and c.op in names


def test_text_edits_change_the_name_key():
    def key(text):
        try:
            return text_key(text)
        except ValueError:  # e.g. merged syllables now carry two tones
            return None

    rng = random.Random(4)
    assert all(key(corrupt("Nguyễn Thị Thúy", rng, "text").text) != key("Nguyễn Thị Thúy") for _ in range(200))


def test_corrupt_returns_none_when_nothing_applies():
    assert corrupt("abc", random.Random(0), "digits") is None
