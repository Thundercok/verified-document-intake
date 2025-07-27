"""Vietnamese addresses across the 2025 administrative reform.

A CCCD issued in 2023 says "Phường 5, Quận 3, TP. Hồ Chí Minh"; a form filled in 2026 says
"Phường Bàn Cờ, Thành phố Hồ Chí Minh". Both can be right. Before 1/7/2025 an address had four
levels (detail, commune, district, province) over 63 provinces; after it, three levels over 34,
with most communes merged and renamed.

What can be decided without a commune gazetteer:
- province: both sides map to the same post-2025 province, or they do not (MISMATCH);
- same era: commune, district and street detail compare as text;
- different eras: commune cannot be compared, so the result is UNDETERMINED at province level.
  Công văn 1027/CTK-CSCL (2025) publishes the new commune codes; adding that table would turn
  this case into a real check.

Era is "pre2025" when a district is present or the province no longer exists, else "post2025".
Parsing is conservative: a component it cannot classify ends classification, so an odd address
yields UNDETERMINED, never a false MATCH.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .result import Check, match, mismatch, undetermined
from .text import clean, fold_diacritics, text_key
from .vn_admin import OLD_TO_NEW, PROVINCE_ALIASES, PROVINCES_POST_2025, PROVINCES_PRE_2025

_PROVINCE_PREFIXES = (("thành", "phố"), ("thủ", "đô"), ("tỉnh",), ("tp",), ("t",))
_KIND_PREFIXES = (
    ("commune", (("phường",), ("xã",), ("thị", "trấn"), ("đặc", "khu"), ("p",), ("x",), ("tt",))),
    ("district", (("quận",), ("huyện",), ("thị", "xã"), ("q",), ("h",), ("tx",))),
    ("district", (("thành", "phố"), ("tp",))),  # a city below a province (pre-2025)
)
_GLUED = re.compile(r"^(p|q)([0-9]+)$")  # "P5", "Q3"
_STREET_FILLER = {"số", "đường", "đ", "sn"}
_SPLIT = re.compile(r"[,;]|\s[-–]\s")
_BRVT = re.compile(r"bà\s*rịa\s*[-–]\s*vũng\s*tàu")

PRE_ONLY = PROVINCES_PRE_2025 - PROVINCES_POST_2025
POST_ONLY = PROVINCES_POST_2025 - PROVINCES_PRE_2025

_ALL_NAMES = PROVINCES_PRE_2025 | PROVINCES_POST_2025
_BY_KEY = {text_key(n): n for n in _ALL_NAMES}
_folded: dict[str, set[str]] = {}
for _n in _ALL_NAMES:
    _folded.setdefault(fold_diacritics(_n), set()).add(_n)
_BY_FOLD = {k: next(iter(v)) for k, v in _folded.items() if len(v) == 1}


def _drop_prefix(
    tok: list[str], prefixes: tuple[tuple[str, ...], ...], folded: bool = False
) -> tuple[bool, list[str]]:
    """Strip a leading kind word. `folded` also accepts it mis-toned ("Tinh", "Tính" for "Tỉnh")."""
    for p in prefixes:
        head = tuple(tok[: len(p)])
        if folded:
            head, p_cmp = tuple(map(fold_diacritics, head)), tuple(map(fold_diacritics, p))
        else:
            p_cmp = p
        if head == p_cmp and len(tok) > len(p):
            return True, tok[len(p) :]
    return False, tok


def resolve_province(text: str) -> str | None:
    """Canonical province name (pre- or post-2025) for a written province, or None.

    Falls back to diacritic folding over the closed list of names, so a mis-toned "Hà Năm" still
    resolves to "hà nam". The verifier therefore compares meaning; the value to emit is the
    canonical name, not the OCR text.
    """
    # Folding is safe here: no province name starts with a word that folds to a prefix.
    _, tok = _drop_prefix(clean(text).split(), _PROVINCE_PREFIXES, folded=True)
    name = " ".join(tok)
    if not name:
        return None
    try:
        if (found := _BY_KEY.get(text_key(name))) is not None:
            return found
    except ValueError:
        pass
    folded = fold_diacritics(name)
    for key in (folded, folded.replace(" ", "")):
        if key in PROVINCE_ALIASES:
            return PROVINCE_ALIASES[key]
    return _BY_FOLD.get(folded)


def _norm_name(tok: list[str]) -> str:
    return " ".join(str(int(t)) if t.isdigit() else t for t in tok)


def _classify(component: str) -> tuple[str | None, str]:
    tok = clean(component).split()
    if len(tok) == 1 and (m := _GLUED.match(tok[0])):
        tok = [m.group(1), m.group(2)]
    for kind, prefixes in _KIND_PREFIXES:
        found, rest = _drop_prefix(tok, prefixes)
        if found:
            return kind, _norm_name(rest)
    return None, _norm_name(tok)


@dataclass(frozen=True)
class Address:
    street: str | None = None
    commune: str | None = None
    district: str | None = None
    province: str | None = None  # canonical name as written, either era

    @property
    def era(self) -> str | None:
        if self.province is None:
            return None
        if self.district is not None or self.province in PRE_ONLY:
            return "pre2025"
        return "post2025"

    @property
    def new_province(self) -> str | None:
        if self.province is None:
            return None
        if self.era == "post2025" or self.province in POST_ONLY:
            return self.province
        return OLD_TO_NEW[self.province]


def parse_address(text: str) -> Address:
    raw = _BRVT.sub("bà rịa vũng tàu", unicodedata.normalize("NFC", text).lower())
    parts = [p for p in _SPLIT.split(raw) if clean(p)]
    if not parts:
        return Address()
    province = resolve_province(parts[-1])
    if province is not None:
        parts = parts[:-1]
    commune = district = None
    street_parts: list[str] = []
    for i in range(len(parts) - 1, -1, -1):
        kind, name = _classify(parts[i])
        if commune is None and kind == "commune":
            commune = name
        elif commune is None and district is None and kind == "district":
            district = name
        else:
            street_parts = parts[: i + 1]
            break
    street_tok = [t for t in clean(" ".join(street_parts)).split() if t not in _STREET_FILLER]
    return Address(_norm_name(street_tok) or None, commune, district, province)


def _same(a: str, b: str) -> bool:
    try:
        return text_key(a) == text_key(b)
    except ValueError:
        return False


def compare_addresses(a: str | Address, b: str | Address, verifier: str = "V_ADDR") -> Check:
    """Detail starts with the deepest level that agrees: full, commune, province or none."""
    pa = a if isinstance(a, Address) else parse_address(a)
    pb = b if isinstance(b, Address) else parse_address(b)
    if pa.province is None or pb.province is None:
        return undetermined(verifier, "none: province not recognised")
    if pa.new_province != pb.new_province:
        return mismatch(verifier, f"none: {pa.new_province} vs {pb.new_province}")
    if pa.era != pb.era:
        return undetermined(verifier, "province: written in different eras, commune needs a gazetteer")
    if pa.era == "pre2025" and pa.province != pb.province:
        return mismatch(verifier, f"none: pre-2025 {pa.province} vs {pb.province}")
    if pa.district and pb.district and not _same(pa.district, pb.district):
        return mismatch(verifier, f"province: district {pa.district} vs {pb.district}")
    if not pa.commune or not pb.commune:
        return undetermined(verifier, "province: commune missing on one side")
    if not _same(pa.commune, pb.commune):
        return mismatch(verifier, f"province: commune {pa.commune} vs {pb.commune}")
    if pa.era == "pre2025" and not (pa.district and pb.district):
        # "Phường 5" exists in many districts of the same city.
        return undetermined(verifier, "province: commune agrees but district missing")
    if not pa.street or not pb.street:
        return undetermined(verifier, "commune: street detail missing on one side")
    if not _same(pa.street, pb.street):
        return mismatch(verifier, f"commune: street {pa.street} vs {pb.street}")
    return match(verifier, "full")
