"""Typicality checks: is a value one diacritic away from a typical one?

Comparison cannot see an error both copies share. Real OCR makes such errors systematically:
the same engine drops the same mark on the card and on the form ("Trần" -> "Trân", "Đỗ" -> "Đô",
"Thụy" -> "Thuy", "Ấp" -> "Áp"), so the two copies agree on a wrong value. The evidence has to
come from outside the pair: what Vietnamese names and address words usually are.

The rule is a *near miss*: a word that is not in the lexicon but folds (diacritics stripped) to a
word that is. Such a word is far more often a misread of the typical word than a rare spelling.
A word with no folded neighbour in the lexicon (a rare or foreign name) is not judged at all, so
the check never penalises a name merely for being unusual.

A near miss gives UNDETERMINED, not MISMATCH: it is a reason to look, not proof. People named
"Nguyên" or "Thuy" exist; their records go to a reviewer, which costs coverage but never risk.

The word lists are general knowledge of Vietnamese naming, written independently of the synthetic
generator's pools (`document_intake.synth.people`) so that an evaluation on synthetic data is not
circular.
"""

from __future__ import annotations

from .result import Check, match, undetermined
from .text import clean, fold_diacritics, syllable_key

SURNAMES = frozenset(
    """
    nguyễn trần lê phạm hoàng huỳnh phan vũ võ đặng bùi đỗ hồ ngô dương lý đào đoàn vương trịnh
    trương lâm phùng mai tô hà tạ lương đinh cao châu chu lưu kiều quách thái tăng từ diệp đàm
    đồng la lại mạc mã nghiêm ông phí phó thân thạch tiêu tôn triệu trình âu bạch biện cù doãn
    giang hàn hứa khổng khúc kim lò lục mạnh nông ninh tống ung vi viên hầu khương lã lữ nhâm ôn
    phương quan sầm sơn thi trang uông khuất đường dư lạc lỗ mông nhan quang văn hoa đậu
    """.split()
)

# Syllables common as middle or given names. Includes words that are near misses of surnames
# but are ordinary given names ("Trân", "Nguyên", "Đăng"): position decides which list applies.
NAME_SYLLABLES = frozenset(
    """
    an anh ánh ân bá bách bạch bảo bắc bằng bích biên bình bông bửu ca cát cẩm cầm cần cảnh chánh
    châu chi chí chiến chinh chính chung công cúc cương cường danh dân diễm diệp diệu dung dũng
    duy duyên dương đan đang đăng đạt điệp định đoan đông đức gấm gia giang giao hà hạ hải hân hạnh
    hào hảo hằng hậu hiền hiển hiệp hiếu hiểu hoa hòa hóa hoài hoan hoàn hoàng hoành hồng hợp
    huân huấn huệ hùng hưng hương hường hữu huy huyền huỳnh kha khải khang khánh khanh khoa khôi
    khuê khương kiên kiệt kiều kim kỳ lam lan lâm lành lễ lệ liên liêm liễu linh loan lộc lợi
    long lực luân luận lương ly lý mai mạnh mẫn minh mơ mỹ my nam nga ngân nghĩa ngọc nguyên
    nguyệt nhã nhàn nhân nhật nhi nhiên nhu như nhung oanh phát phi phong phú phúc phụng phước
    phương phượng quân quang quảng quế quốc quý quyên quyết quỳnh sang sáng sơn sương tài tâm tân thảo
    tấn thạch thái thắm thắng thanh thành thảo thắng thi thịnh thoa thông thơ thu thuần thuận
    thục thùy thúy thủy thụy thư thương tiên tiến tín tịnh toàn toản trà trâm trân trang trí
    triết trinh trọng trung trúc trường tú tuấn tùng tuyền tuyết tường uyên văn vân vi việt vinh
    vĩnh võ vũ vương vy xuân yên yến thị
    """.split()
)

# Words that open the detail line of a rural address and are followed by a number: "Ấp 12",
# "Thôn 3", "Tổ 5", "Khu phố 2".
ADDRESS_UNIT_WORDS = frozenset("ấp thôn xóm tổ khóm khu phố bản buôn sóc làng đội cụm dân".split())


def _index(words: frozenset[str]) -> tuple[frozenset[tuple[str, str]], dict[str, list[str]]]:
    keys = frozenset(syllable_key(w) for w in words)
    by_fold: dict[str, list[str]] = {}
    for w in sorted(words):
        by_fold.setdefault(fold_diacritics(w), []).append(w)
    return keys, by_fold


_SURNAMES = _index(SURNAMES)
_NAMES = _index(NAME_SYLLABLES)
_UNITS = _index(ADDRESS_UNIT_WORDS)


def near_miss(word: str, lexicon: tuple[frozenset[tuple[str, str]], dict[str, list[str]]]) -> list[str]:
    """The lexicon words `word` may be a misread of: empty if it is in the lexicon or has no
    folded neighbour there."""
    keys, by_fold = lexicon
    try:
        if syllable_key(word) in keys:
            return []
    except ValueError:  # two tone marks: not a Vietnamese syllable, certainly a misread
        pass
    return by_fold.get(fold_diacritics(word), [])


def check_name_typical(name: str, verifier: str = "V_NAME_LEX") -> Check:
    """UNDETERMINED if the surname or any other syllable is a near miss of a typical one.

    The first syllable is judged against surnames, the rest against middle and given names.
    """
    tok = clean(name).split()
    if not tok:
        return undetermined(verifier, "empty name")
    for i, w in enumerate(tok):
        if alts := near_miss(w, _SURNAMES if i == 0 else _NAMES):
            return undetermined(verifier, f"{w!r} is a near miss of {'/'.join(alts)}")
    return match(verifier, "typical")


def check_address_typical(street: str | None, verifier: str = "V_ADDR_LEX") -> Check:
    """UNDETERMINED if a word before the first number of the detail line ("Áp 12") is a near miss
    of an address unit word. Words not followed by a number are street or hamlet names, which are
    open-class ("Tô Hiến Thành" is a street, not "Tổ"), and are not judged."""
    tok = clean(street or "").split()
    first_num = next((i for i, t in enumerate(tok) if t.isdigit()), None)
    for w in tok[: first_num or 0]:
        if alts := near_miss(w, _UNITS):
            return undetermined(verifier, f"{w!r} is a near miss of {'/'.join(alts)}")
    return match(verifier, "typical")
