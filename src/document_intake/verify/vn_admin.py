"""Vietnamese province-level administrative data, before and after the 2025 reform.

Sources:
- CCCD province codes: Phụ lục 1, Thông tư 07/2016/TT-BCA (the code is the province where the
  birth was registered). Codes were not renumbered by the 2025 merger, so a CCCD keeps naming
  a pre-2025 province.
- Merger: Nghị quyết 202/2025/QH15 (effective 12/6/2025; local government from 1/7/2025):
  63 provinces -> 34 (11 unchanged, 23 formed by merging). The district level was abolished
  at the same time. The list below was compiled from secondary summaries of the resolution;
  `tests/test_verify_admin.py` checks its internal consistency (63 -> 34, each old province
  mapped exactly once), not its legal accuracy.

Names are stored in canonical lower-case Vietnamese without the "tỉnh"/"thành phố" prefix.
"""

from __future__ import annotations

# Code (digits 1-3 of a CCCD) -> pre-2025 province.
CCCD_PROVINCE_CODES: dict[str, str] = {
    "001": "hà nội",
    "002": "hà giang",
    "004": "cao bằng",
    "006": "bắc kạn",
    "008": "tuyên quang",
    "010": "lào cai",
    "011": "điện biên",
    "012": "lai châu",
    "014": "sơn la",
    "015": "yên bái",
    "017": "hòa bình",
    "019": "thái nguyên",
    "020": "lạng sơn",
    "022": "quảng ninh",
    "024": "bắc giang",
    "025": "phú thọ",
    "026": "vĩnh phúc",
    "027": "bắc ninh",
    "030": "hải dương",
    "031": "hải phòng",
    "033": "hưng yên",
    "034": "thái bình",
    "035": "hà nam",
    "036": "nam định",
    "037": "ninh bình",
    "038": "thanh hóa",
    "040": "nghệ an",
    "042": "hà tĩnh",
    "044": "quảng bình",
    "045": "quảng trị",
    "046": "thừa thiên huế",
    "048": "đà nẵng",
    "049": "quảng nam",
    "051": "quảng ngãi",
    "052": "bình định",
    "054": "phú yên",
    "056": "khánh hòa",
    "058": "ninh thuận",
    "060": "bình thuận",
    "062": "kon tum",
    "064": "gia lai",
    "066": "đắk lắk",
    "067": "đắk nông",
    "068": "lâm đồng",
    "070": "bình phước",
    "072": "tây ninh",
    "074": "bình dương",
    "075": "đồng nai",
    "077": "bà rịa vũng tàu",
    "079": "hồ chí minh",
    "080": "long an",
    "082": "tiền giang",
    "083": "bến tre",
    "084": "trà vinh",
    "086": "vĩnh long",
    "087": "đồng tháp",
    "089": "an giang",
    "091": "kiên giang",
    "092": "cần thơ",
    "093": "hậu giang",
    "094": "sóc trăng",
    "095": "bạc liêu",
    "096": "cà mau",
}

PROVINCES_PRE_2025: frozenset[str] = frozenset(CCCD_PROVINCE_CODES.values())

# Post-2025 province -> the pre-2025 provinces it absorbed (itself first when it kept the name).
MERGER_2025: dict[str, tuple[str, ...]] = {
    # 11 unchanged
    "hà nội": ("hà nội",),
    "huế": ("thừa thiên huế",),
    "lai châu": ("lai châu",),
    "điện biên": ("điện biên",),
    "sơn la": ("sơn la",),
    "lạng sơn": ("lạng sơn",),
    "quảng ninh": ("quảng ninh",),
    "thanh hóa": ("thanh hóa",),
    "nghệ an": ("nghệ an",),
    "hà tĩnh": ("hà tĩnh",),
    "cao bằng": ("cao bằng",),
    # 23 merged
    "tuyên quang": ("tuyên quang", "hà giang"),
    "lào cai": ("lào cai", "yên bái"),
    "thái nguyên": ("thái nguyên", "bắc kạn"),
    "phú thọ": ("phú thọ", "vĩnh phúc", "hòa bình"),
    "bắc ninh": ("bắc ninh", "bắc giang"),
    "hưng yên": ("hưng yên", "thái bình"),
    "hải phòng": ("hải phòng", "hải dương"),
    "ninh bình": ("ninh bình", "hà nam", "nam định"),
    "quảng trị": ("quảng trị", "quảng bình"),
    "đà nẵng": ("đà nẵng", "quảng nam"),
    "quảng ngãi": ("quảng ngãi", "kon tum"),
    "gia lai": ("gia lai", "bình định"),
    "khánh hòa": ("khánh hòa", "ninh thuận"),
    "lâm đồng": ("lâm đồng", "đắk nông", "bình thuận"),
    "đắk lắk": ("đắk lắk", "phú yên"),
    "hồ chí minh": ("hồ chí minh", "bình dương", "bà rịa vũng tàu"),
    "đồng nai": ("đồng nai", "bình phước"),
    "tây ninh": ("tây ninh", "long an"),
    "cần thơ": ("cần thơ", "sóc trăng", "hậu giang"),
    "vĩnh long": ("vĩnh long", "bến tre", "trà vinh"),
    "đồng tháp": ("đồng tháp", "tiền giang"),
    "cà mau": ("cà mau", "bạc liêu"),
    "an giang": ("an giang", "kiên giang"),
}

PROVINCES_POST_2025: frozenset[str] = frozenset(MERGER_2025)

OLD_TO_NEW: dict[str, str] = {old: new for new, olds in MERGER_2025.items() for old in olds}

# Spelling variants and abbreviations seen on forms, keyed by the diacritic-folded form
# (see text.fold_diacritics). Values are canonical names from either era.
PROVINCE_ALIASES: dict[str, str] = {
    "hcm": "hồ chí minh",
    "tphcm": "hồ chí minh",
    "sai gon": "hồ chí minh",
    "ho chi minh": "hồ chí minh",
    "hn": "hà nội",
    "brvt": "bà rịa vũng tàu",
    "ba ria": "bà rịa vũng tàu",
    "vung tau": "bà rịa vũng tàu",
    "thua thien hue": "thừa thiên huế",
    "tt hue": "thừa thiên huế",
    "dac lac": "đắk lắk",
    "dak lak": "đắk lắk",
    "daklak": "đắk lắk",
    "dac nong": "đắk nông",
    "dak nong": "đắk nông",
    "daknong": "đắk nông",
    "kontum": "kon tum",
    "bac can": "bắc kạn",
    "hoa binh": "hòa bình",
    "thanh hoa": "thanh hóa",
    "khanh hoa": "khánh hòa",
}
