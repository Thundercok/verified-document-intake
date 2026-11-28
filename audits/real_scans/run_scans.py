"""Real scans with real seals: document number, issue date and the signer block (see PREREG.md).

Input: PDFs from vanban.chinhphu.vn in data/private/vbcp/pdf/<listing index>.pdf and the listing
in data/private/vbcp/docs.json (number and date per document, the ground truth).

Per document:
- page 1 is rendered at 300 dpi; its top 30% is the header crop (number and date);
- on the last page, the largest blob of red ink is taken as the seal, and a crop around it is the
  seal crop (the signer's title is printed next to or under the seal);
- each crop is read as scanned and after red-ink dropout (`audits/ocr_pilot/dropout.py`), by
  Apple Vision, and the header also by Tesseract `vie` (page segmentation 3).

Images and OCR text stay under data/private/vbcp/ (gitignored). The report has aggregates only.

Usage: uv run python audits/real_scans/run_scans.py [--md audits/real_scans/RESULTS.md] [--skip-ocr]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
from datetime import date
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ocr_pilot"))
from analyze import binom_cdf, cp_upper, pct  # noqa: E402
from dropout import dropout, red_mask  # noqa: E402

PRIV = Path(os.environ.get("VBCP_DIR", "data/private/vbcp"))  # VBCP_DIR=data/private/vbcp2: confirmation batch
RENDER = Path("audits/real_scans/work/render_pages")
VISION = Path("audits/ocr_pilot/work/vision_ocr")
HEADER_SHARE = 0.30
RED_PAGE = 0.002  # PREREG: a last page "carries red ink" above this share
TODAY = date(2026, 11, 25)
TITLES = (
    "THỦ TƯỚNG", "BỘ TRƯỞNG", "THỨ TRƯỞNG", "CHỦ NHIỆM", "CHỦ TỊCH", "TỔNG THƯ KÝ", "THỐNG ĐỐC",
    "TỔNG KIỂM TOÁN", "CHÁNH ÁN", "VIỆN TRƯỞNG", "GIÁM ĐỐC", "CỤC TRƯỞNG", "VỤ TRƯỞNG",
    "CHÁNH VĂN PHÒNG", "TRƯỞNG BAN", "TỔNG CỤC TRƯỞNG", "BỘ TRƯỞNG, CHỦ NHIỆM",
)  # fmt: skip


def canon(s: str) -> str:
    """Compare numbers as printed: NFC, no spaces, Icelandic Ð (same glyph) read as Đ."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s)).replace("Ð", "Đ").replace("đ", "đ")


NUM_RE = re.compile(r"(\d+/(?:\d{4}/)?[A-ZĐÐ][A-ZĐÐa-z0-9\-]*)")
DATE_RE = re.compile(r"ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.IGNORECASE)


def read_number(text: str) -> str | None:
    t = unicodedata.normalize("NFC", text)
    t = re.sub(r"\s*([/\-])\s*", r"\1", t)
    t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)  # "23 03/QĐ" -> "2303/QĐ"
    at = t.find("Số")
    m = NUM_RE.search(t, at if at >= 0 else 0) or NUM_RE.search(t)
    return canon(m.group(1)) if m else None


def read_date(text: str) -> tuple[int, int, int] | None:
    m = DATE_RE.search(unicodedata.normalize("NFC", text))
    return tuple(int(g) for g in m.groups()) if m else None  # type: ignore[return-value]


DOTS = re.compile(r"[.…]{2,}|…")
DATE2_RE = re.compile(r",\s*ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.IGNORECASE)


def read_number2(text: str) -> str | None:
    """Post hoc (written after seeing v1's errors): drop dotted leaders and read only right after "Số"."""
    t = DOTS.sub("", unicodedata.normalize("NFC", text))
    at = t.find("Số")
    if at < 0:
        return None
    t = re.sub(r"\s*([/\-])\s*", r"\1", t[at + 2 : at + 60])
    t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)
    m = re.match(r"\s*[:.]?\s*(\d+/(?:\d{4}/)?[A-ZĐÐ][A-ZĐÐa-z0-9\-]*)", t)
    return canon(m.group(1)) if m else None


def read_date2(text: str) -> tuple[int, int, int] | None:
    """Post hoc: drop dotted leaders and take only the place-date line ("Hà Nội, ngày ..."), never a
    date quoted in the title."""
    m = DATE2_RE.search(DOTS.sub("", unicodedata.normalize("NFC", text)))
    return tuple(int(g) for g in m.groups()) if m else None  # type: ignore[return-value]


def checks_pass(num: str | None, d: tuple[int, int, int] | None) -> bool:
    """Deterministic checks, no truth: a well-formed number, a valid past date, and a year inside
    the number (if any) equal to the date's year."""
    if num is None or d is None:
        return False
    try:
        when = date(d[2], d[1], d[0])
    except ValueError:
        return False
    if not date(1945, 9, 2) <= when <= TODAY:
        return False
    y = re.match(r"\d+/(\d{4})/", num)
    return not (y and int(y.group(1)) != d[2])


# --- v3 (written 2026-11-26 after the confirmation batch killed v2; developed on batches 1 and 2) ---
NUM3_RE = re.compile(r"\s*[:.]?\s*(\d+/(?:\d{4}/)?[A-ZĐÐ][A-ZĐÐa-z0-9&\-]*)")
# Normative documents carry the year: "84/2026/TT-BXD". In the 498 listed numbers of batches 1-2,
# TT, NĐ and QH always do and VBHN does in 119 of 121 (the 2 others are abstained on, not wrong).
YEAR_TYPES = ("TT", "NĐ", "VBHN", "TTLT", "QH")
QDATE_RE = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})")


def read_number3(text: str) -> str | None:
    """v2, with "&" allowed in the symbol ("155/QĐ-BCĐNO&TTBĐS")."""
    t = DOTS.sub("", unicodedata.normalize("NFC", text))
    at = t.find("Số")
    if at < 0:
        return None
    t = re.sub(r"\s*([/\-])\s*", r"\1", t[at + 2 : at + 60])
    t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)
    m = NUM3_RE.match(t)
    return canon(m.group(1)) if m else None


def checks_pass3(num: str | None, d: tuple[int, int, int] | None) -> bool:
    """v2's checks, plus: a normative type must carry a year segment. A slash read as "1"
    ("7/2026/VBHN" -> "712026/VBHN") loses that segment and is rejected."""
    if not checks_pass(num, d):
        return False
    parts = num.split("/")  # type: ignore[union-attr]
    kind = parts[-1].split("-")[0]
    has_year = len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[1]) is not None
    return has_year or not any(kind.startswith(k) for k in YEAR_TYPES)


def read_qwen(text: str) -> tuple[str | None, tuple[int, int, int] | None]:
    """Qwen's two-line answer (header_prompt.txt): the number, then dd/mm/yyyy."""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    num = read_number3("Số: " + lines[0]) if lines else None
    m = QDATE_RE.search(lines[1]) if len(lines) > 1 else None
    return num, (tuple(int(g) for g in m.groups()) if m else None)  # type: ignore[return-value]


# --- v4 (written 2026-11-26 after the third batch; developed on batches 1-3, 726 documents) ---
# Vision's read is turned into every number it could stand for (a slash read as "|", "(", ".",
# "1" or a space; digits split by a space), and the document is accepted only if exactly one of
# them passes checks_pass3 and equals Qwen's read. The value kept is Vision's.
SO_RE = re.compile(r"(?:S[ốôoóồổ6]|s[ốô])\s*[:.]?\s*")
TAIL4 = r"[A-ZĐÐ][A-ZĐÐa-z0-9&.\-]*[A-Za-z0-9ĐÐ]"
NUM4_RE = re.compile(
    rf"(\d+)\s*((?:[/|(.]{{1,2}}|1)?)\s*(?:(\d{{4}})\s*(?:[/|(.]{{1,2}}|1)?\s*)?({TAIL4})(?![/\w&.\-])"
)
HOMOGLYPHS = str.maketrans("АВЕКМНОРСТХ", "ABEKMHOPCTX")  # Cyrillic capitals found in the listing
FOLD = str.maketrans("ĐÐđ", "DDd")  # Qwen often drops the stroke of Đ


def read_numbers4(text: str, so: re.Pattern = SO_RE) -> list[str]:
    t = DOTS.sub("", unicodedata.normalize("NFC", text))
    for at in so.finditer(t):
        seg = re.sub(r"\s*([/\-])\s*", r"\1", t[at.end() : at.end() + 50])
        out = []
        for s in dict.fromkeys((seg, re.sub(r"(?<=\d)\s+(?=\d)", "", seg))):
            m = NUM4_RE.match(s)
            if not m:
                continue
            num, sep, year, tail = m.groups()
            reads = [(num, year)]
            if not sep and len(num) > 1 and num.endswith("1"):  # "22321QĐ" -> "2232/QĐ"
                reads.append((num[:-1], year))
            split = re.fullmatch(r"(\d+)1(\d{4})", num)
            if split and not year:  # "712026/VBHN" -> "7/2026/VBHN"
                reads.append(split.groups())
            out += [canon(f"{n}/{y + '/' if y else ''}{tail}") for n, y in reads]
        if out:
            return list(dict.fromkeys(out))
    return []


def truth4(num: str) -> str:
    """The listing's number for scoring v4: canon() plus Cyrillic look-alikes as Latin."""
    return canon(num).translate(HOMOGLYPHS)


def agree4(vn: str, vd: tuple[int, int, int], qtext: str) -> bool:
    lines = [x.strip() for x in qtext.splitlines() if x.strip()]
    qn = (read_numbers4("Số: " + lines[0]) or [None])[0] if lines else None
    m = QDATE_RE.search(lines[1]) if len(lines) > 1 else None
    qd = tuple(int(g) for g in m.groups()) if m else None
    same_num = qn is not None and vn.translate(FOLD) == qn.translate(FOLD)
    return same_num and qd in (vd, (vd[1], vd[0], vd[2]))  # day and month may be swapped


EMBLEM_RE = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\s+\d{1,2}:\d{2}")
EMBLEM_DAYS = 14  # issue date to e-signature time; 0-14 days for 90% of the 469 dev pages that print it


def emblem_ok(text: str, d: tuple[int, int, int], days: int = EMBLEM_DAYS) -> bool:
    """A second printed date on the same page: the e-signature emblem ("Thời gian ký: 22.09.2026
    13:57"). If it is there, the issue date must fall 0-14 days before it. Catches a day read short
    ("ngày21tháng" read as 2) that both engines agree on."""
    try:
        sig = [date(int(y), int(m), int(dd)) for dd, m, y in EMBLEM_RE.findall(text)]
        gap = (min(sig) - date(d[2], d[1], d[0])).days if sig else None
    except ValueError:
        return True  # an unreadable emblem says nothing
    return gap is None or 0 <= gap <= days


def read_v4(text: str, qtexts: list[str]) -> tuple[str | None, tuple[int, int, int] | None]:
    """Accepted (number, date), or (None, date). qtexts: Qwen reads, tried in order."""
    d = read_date2(text)
    if d is None or not emblem_ok(text, d):
        return None, d
    cands = [n for n in read_numbers4(text) if checks_pass3(n, d)]
    for q in qtexts:
        hits = [n for n in cands if agree4(n, d, q)]
        if len(hits) == 1:
            return hits[0], d
    return None, d


def qwen_number(qtext: str, so: re.Pattern = SO_RE) -> str | None:
    lines = [x.strip() for x in qtext.splitlines() if x.strip()]
    return canon((read_numbers4("Số: " + lines[0], so) or [None])[0] or "") or None if lines else None


CODES = {
    x.strip()
    for x in (Path(__file__).parent / "issuer_codes.txt").read_text(encoding="utf-8").splitlines()
    if x.strip() and not x.startswith("#")
}


def merge_d(vn: str, qn: str | None) -> str:
    """v5: v4 wrote Vision's spelling, and Vision once dropped the stroke of Đ ("1279/QD-TTg",
    batch 4's only error). Qwen both drops it and adds it ("BGDĐT" read "BGĐĐT"), so neither
    engine's Đ is trusted alone: segment by segment, Qwen's spelling replaces Vision's only when
    Vision's is not a known code (issuer_codes.txt) and Qwen's is."""
    if qn is None or qn.translate(FOLD) != vn.translate(FOLD):
        return vn
    sv, sq = re.split(r"([/-])", vn), re.split(r"([/-])", qn)
    if len(sv) != len(sq):
        return vn
    return "".join(q if v != q and v not in CODES and q in CODES else v for v, q in zip(sv, sq, strict=True))


def read_v5(text: str, qtexts: list[str]) -> tuple[str | None, tuple[int, int, int] | None]:
    """read_v4, then merge_d with the Qwen read that agreed."""
    d = read_date2(text)
    if d is None or not emblem_ok(text, d):
        return None, d
    cands = [n for n in read_numbers4(text) if checks_pass3(n, d)]
    for q in qtexts:
        hits = [n for n in cands if agree4(n, d, q)]
        if len(hits) == 1:
            return merge_d(hits[0], qwen_number(q)), d
    return None, d


# --- v6 (written 2026-11-27 after the fifth batch; developed on batches 4-5) ---
# Batch 5 missed the coverage bar on consolidated texts (VBHN), for two reasons:
# 1. VBHN numbers dropped the year in 2026: "37/VBHN-BXD", not "37/2026/VBHN-BXD" (no year in 0 of
#    42 listed VBHN in batch 1, 48 of 86 in batch 4, 127 of 127 in batch 5). checks_pass3 demanded
#    the year. checks_pass6 drops that demand for VBHN, but caps the number at 4 digits so that a
#    slash read as "1" ("7/2026/VBHN" -> "712026/VBHN") still fails.
# 2. A VBHN may print its number and date only in the authentication block at the end of the main
#    text ("XÁC THỰC VĂN BẢN HỢP NHẤT"), laid out like a header. If page 1 gives no accept, the
#    block is found in the PDF text layer, cropped from the rendered page, and read by Vision and
#    Qwen exactly as a header; only a VBHN number is accepted from it.
AUTH_RE = re.compile(r"XÁC\s*THỰC\s*VĂN\s*BẢN\s*HỢP\s*NHẤT")
AUTH_TOP, AUTH_BOTTOM = 0.03, 0.08  # crop, as shares of the page height around the block's title


def checks_pass6(num: str | None, d: tuple[int, int, int] | None) -> bool:
    if not checks_pass(num, d):
        return False
    parts = num.split("/")  # type: ignore[union-attr]
    kind = parts[-1].split("-")[0]
    if kind == "VBHN" and len(parts) == 2:
        return len(parts[0]) <= 4
    has_year = len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[1]) is not None
    return has_year or not any(kind.startswith(k) for k in YEAR_TYPES)


def auth_locate(pdf: Path) -> tuple[int, float] | None:
    """(0-based page, share of the page height from the top) of the VBHN authentication title, from
    the text layer; the last page that has it. None if no page has it or it cannot be placed."""
    from pypdf import PdfReader

    pages = PdfReader(pdf).pages
    for k in range(len(pages) - 1, -1, -1):
        frags: list[tuple[str, float]] = []

        def visit(text, cm, tm, _font, _size, frags=frags):
            if text.strip():
                frags.append((unicodedata.normalize("NFC", text), tm[4] * cm[1] + tm[5] * cm[3] + cm[5]))

        try:
            full = unicodedata.normalize("NFC", pages[k].extract_text(visitor_text=visit) or "")
        except Exception:  # noqa: BLE001 - an unreadable page has no block
            continue
        if not AUTH_RE.search(full):
            continue
        ys = [
            y
            for i, (t, y) in enumerate(frags)
            if "XÁC" in t and AUTH_RE.search("".join(x for x, _ in frags[i : i + 8]))
        ]
        if not ys:
            return None
        box = pages[k].mediabox
        return k, 1 - (min(ys) - float(box.bottom)) / float(box.height)
    return None


# Batch 6: 59 of 98 text-layer VBHN had a block auth_locate missed. Two causes: the National Assembly
# Office's text layer is an OCR layer with a broken font ("xAc THl/C VAN BAN HQP NHA T"), and in
# clean layers the phrase is split over fragments in ways the 8-fragment window misses. v7 folds
# every fragment (marks stripped, upper case, A-Z0-9 only), joins them with an index map, and looks
# for a pattern that allows the garbled letters; the block is placed at the fragment where the match
# starts. Where v6 found a block, v7 finds the same page and the same crop (125 of 125, in-sample).
AUTH7_RE = re.compile(r"XACTH\w{0,3}VANBANH\w{0,3}PN(?:H|II|B)AT")


def fold7(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("Đ", "D").replace("đ", "d"))
    return re.sub(r"[^A-Z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).upper())


def auth_locate7(pdf: Path) -> tuple[int, float] | None:
    """As auth_locate, with the folded, tolerant match. None if no page has it."""
    from pypdf import PdfReader

    pages = PdfReader(pdf).pages
    for k in range(len(pages) - 1, -1, -1):
        frags: list[tuple[str, float]] = []

        def visit(text, cm, tm, _font, _size, frags=frags):
            if text.strip():
                frags.append((fold7(text), tm[4] * cm[1] + tm[5] * cm[3] + cm[5]))

        try:
            pages[k].extract_text(visitor_text=visit)
        except Exception:  # noqa: BLE001 - an unreadable page has no block
            continue
        joined, owner = "", []
        for j, (t, _) in enumerate(frags):
            joined += t
            owner += [j] * len(t)
        hits = list(AUTH7_RE.finditer(joined))
        if not hits:
            continue
        box = pages[k].mediabox
        share = 1 - (frags[owner[hits[-1].start()]][1] - float(box.bottom)) / float(box.height)
        return (k, share) if 0 <= share <= 1 else None
    return None


def accept6(text: str, q: str | None, vbhn_only: bool) -> tuple[str | None, tuple[int, int, int] | None]:
    d = read_date2(text)
    if q is None or d is None or not emblem_ok(text, d):
        return None, d
    cands = [n for n in read_numbers4(text) if checks_pass6(n, d)]
    if vbhn_only:
        cands = [n for n in cands if n.split("/")[-1].startswith("VBHN")]
    hits = [n for n in cands if agree4(n, d, q)]
    return (merge_d(hits[0], qwen_number(q)), d) if len(hits) == 1 else (None, d)


def read_v6(text: str, q: str | None, atext: str | None, aq: str | None) -> tuple[str | None, tuple | None, str]:
    """Page-1 header first; if it gives no accept, the VBHN authentication block. Returns (number,
    date, where): where is "page1", "auth" or ""."""
    n, d = accept6(text, q, vbhn_only=False)
    if n:
        return n, d, "page1"
    if atext is not None and aq is not None:
        n2, d2 = accept6(atext, aq, vbhn_only=True)
        if n2:
            return n2, d2, "auth"
    return None, d, ""


# --- v8 (written 2026-11-27 after the seventh batch; developed on batches 1-7, 2,726 documents) ---
# Batch 7's two errors were handwritten numbers that Vision and Qwen read the same wrong way.
# A. Vision read "2491QĐ-TTg" with no slash, which gives two candidates: 2491, and 249 with the slash
#    read as "1". Qwen, looking at the same unclear pixels, said 249, and v7 took it. When more than
#    one candidate passes the checks, Qwen is not an independent tie-breaker, so v8 abstains.
# B. "2615" was read as 2645 by both. Numbers in one register rise with the date. Within a batch the
#    accepts are grouped by register (the part after the number, the number of "/" segments, and the
#    year of the date); two conflict when the higher number carries the earlier date. The accepts in
#    the most conflicts are dropped (all of them on a tie, so nothing depends on order) until none
#    conflict. B uses only the batch's own reads; with few documents from one register it does nothing.
# In-sample on batches 1-7 (v7: 2,114 accepts, 2 wrong): A and B drop both errors and 18 correct.


def accept8(text: str, q: str | None, vbhn_only: bool) -> tuple[str | None, tuple[int, int, int] | None]:
    """accept6, abstaining when more than one candidate passes the checks (rule A)."""
    d = read_date2(text)
    if q is None or d is None or not emblem_ok(text, d):
        return None, d
    cands = [n for n in read_numbers4(text) if checks_pass6(n, d)]
    if len(cands) > 1:
        return None, d
    return accept6(text, q, vbhn_only)


def read_v8(text: str, q: str | None, atext: str | None, aq: str | None) -> tuple[str | None, tuple | None, str]:
    """read_v6 with accept8. Rule B is applied afterwards, over the batch (register_drop)."""
    n, d = accept8(text, q, vbhn_only=False)
    if n:
        return n, d, "page1"
    if atext is not None and aq is not None:
        n2, d2 = accept8(atext, aq, vbhn_only=True)
        if n2:
            return n2, d2, "auth"
    return None, d, ""


def register_drop(accepts: list[tuple[int, str, tuple[int, int, int]]]) -> set[int]:
    """Rule B. accepts: (id, number, (d, m, y)). Returns the ids to drop."""
    groups: dict[tuple, list[tuple[int, int, date]]] = {}
    for i, num, (dd, mm, yy) in accepts:
        parts = num.split("/")
        if parts[0].isdigit():
            groups.setdefault((parts[-1], len(parts), yy), []).append((i, int(parts[0]), date(yy, mm, dd)))
    out: set[int] = set()
    for xs in groups.values():
        while True:
            c = {a[0]: sum((a[1] < b[1] and a[2] > b[2]) or (b[1] < a[1] and b[2] > a[2]) for b in xs) for a in xs}
            top = max(c.values(), default=0)
            if top == 0:
                break
            worst = {i for i, k in c.items() if k == top}
            out |= worst
            xs = [x for x in xs if x[0] not in worst]
    return out


# --- v9 (written 2026-11-27 after the eighth batch; developed on batches 1-8, 3,226 documents) ---
# v8 was certified on batch 8 but accepted 62.6%. Three changes, each aimed at a measured loss:
# L. Laws and National Assembly resolutions ("…/2025/QH15", "…/2026/UBTVQH16") print no date on
#    page 1; it is in the closing sentence "… thông qua ngày 25 tháng 6 năm 2025" on the last page.
#    When page 1 has no date, Vision's read of the last page gives the date (the last such sentence),
#    Qwen reads the same page with passed_prompt.txt, and both must agree. The number still comes from
#    page 1, and its year must equal the date's year (checks_pass6). In-sample, Vision alone found the
#    sentence in 98 of 137 such documents; 97 matched the listing, the other had the year wrong
#    (2023 for 2025), which the year check rejects. The e-signature emblem on page 1 is signed after
#    the law is promulgated, not on the day it is passed: on the 146 such documents of batches 1-8 that
#    print one, the listing date to the emblem is 0-45 days but for one at 244. Rule L checks the
#    emblem with 0-45 days (EMBLEM_DAYS_L, set on batches 1-8) instead of 0-14.
# T. Vision misreads letters in the issuer part ("NQ-UBTVQH1S", "NO-UBTVQHIS") where Qwen does not,
#    and v8 then abstains. v9 compares the part after the last "/" under OCR look-alikes (O Q 0,
#    I l | 1, S 5, Đ D). Where Vision and Qwen differ there, a segment is taken from the engine whose
#    segment is in issuer_codes9.txt (segments seen at least twice in the listings of batches 1-8)
#    when the other's is not; if that does not settle it, v9 abstains. Digits before the last "/"
#    must be identical, as before.
# B. Rule B grouped "48/2025/QĐ-UBND" and "53/2025/QĐ-UBND" as one register although they come from
#    different provinces, and dropped 5 correct accepts in batch 8. A local-government tail (UBND,
#    HĐND) names many registers, so rule B now skips it. So does "QH15" alone: laws (93-99/2025/QH15)
#    and resolutions (205-207/2025/QH15) of the National Assembly are numbered apart, and rule L's
#    accepts would otherwise lose 7 correct ones in batches 7-8 (in-sample).
# Rule A is kept.
CODES9 = {
    x.strip()
    for x in (Path(__file__).parent / "issuer_codes9.txt").read_text(encoding="utf-8").splitlines()
    if x.strip() and not x.startswith("#")
}
CONF9 = str.maketrans({"Đ": "D", "Ð": "D", "đ": "d", "O": "0", "Q": "0", "I": "1", "l": "1", "|": "1", "S": "5"})
EMBLEM_DAYS_L = 45
PASSED_RE = re.compile(r"thông\s*qua\s*ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.IGNORECASE)


def merge9(vn: str, qn: str | None) -> str | None:
    """Vision's candidate and Qwen's number, as one number, or None if they do not agree (rule T)."""
    if qn is None or "/" not in vn or "/" not in qn:
        return None
    (vh, vt), (qh, qt) = vn.rsplit("/", 1), qn.rsplit("/", 1)
    if vh != qh or vt.translate(CONF9) != qt.translate(CONF9):
        return None
    sv, sq = vt.split("-"), qt.split("-")
    if len(sv) != len(sq):
        return None
    out = []
    for v, q in zip(sv, sq, strict=True):
        if v == q or (v in CODES9 and q not in CODES9):
            out.append(v)
        elif q in CODES9 and v not in CODES9:
            out.append(q)
        elif v.translate(FOLD) == q.translate(FOLD):
            out.append(v)  # a Đ/D difference no code list settles: Vision's spelling, as merge_d
        else:
            return None
    return f"{vh}/{'-'.join(out)}"


def qwen_date(line: str | None) -> tuple[int, int, int] | None:
    m = QDATE_RE.search(line or "")
    return tuple(int(g) for g in m.groups()) if m else None  # type: ignore[return-value]


def passed_date(text: str | None) -> tuple[int, int, int] | None:
    """The date of the last "thông qua ngày … tháng … năm …" sentence in a page read."""
    hits = PASSED_RE.findall(DOTS.sub("", unicodedata.normalize("NFC", text or "")))
    return tuple(int(g) for g in hits[-1]) if hits else None  # type: ignore[return-value]


def accept9(
    text: str,
    q: str | None,
    vbhn_only: bool,
    d: tuple[int, int, int] | None,
    qd: tuple[int, int, int] | None,
    days: int = EMBLEM_DAYS,
) -> str | None:
    """One accept: d is the date Vision read (page 1, the block, or the last page), qd Qwen's read of it."""
    if q is None or d is None or not emblem_ok(text, d, days) or qd not in (d, (d[1], d[0], d[2])):
        return None
    cands = [n for n in read_numbers4(text) if checks_pass6(n, d)]
    if len(cands) != 1:  # none, or more than one (rule A)
        return None
    if vbhn_only and not cands[0].split("/")[-1].startswith("VBHN"):
        return None
    return merge9(cands[0], qwen_number(q))


def read_v9(
    text: str, q: str | None, atext: str | None, aq: str | None, ptext: str | None, pq: str | None
) -> tuple[str | None, tuple | None, str]:
    """Page 1; else the VBHN block (v7 locator); else, when page 1 has no date, the last page's
    closing sentence (rule L). ptext: Vision's read of the last page; pq: Qwen's (passed_prompt.txt).
    Returns (number, date, where): where is "page1", "auth", "passed" or ""."""
    qlines = [x.strip() for x in (q or "").splitlines() if x.strip()]
    d = read_date2(text)
    n = accept9(text, q, False, d, qwen_date(qlines[1] if len(qlines) > 1 else None))
    if n:
        return n, d, "page1"
    if atext is not None and aq is not None:
        alines = [x.strip() for x in aq.splitlines() if x.strip()]
        d2 = read_date2(atext)
        n2 = accept9(atext, aq, True, d2, qwen_date(alines[1] if len(alines) > 1 else None))
        if n2:
            return n2, d2, "auth"
    if d is None and ptext is not None and pq is not None:
        d3 = passed_date(ptext)
        n3 = accept9(text, q, False, d3, qwen_date(pq), EMBLEM_DAYS_L)
        if n3:
            return n3, d3, "passed"
    return None, d, ""


def register_drop9(accepts: list[tuple[int, str, tuple[int, int, int]]]) -> set[int]:
    """Rule B, skipping tails that name more than one register: local government ("QĐ-UBND" in many
    provinces) and the National Assembly ("QH15" for both laws and resolutions)."""
    many = re.compile(r"UBND|HĐND|QH\d+")
    return register_drop([a for a in accepts if not many.search(a[1].split("/")[-1]) or "UBTVQH" in a[1]])


# --- v10 (written 2026-11-28 after the ninth batch; developed on batches 1-9, 3,726 documents) ---
# v9 met coverage on batch 9 but failed the certificate on one error, and v7 failed it on two: in all
# three, a handwritten page-1 number that Vision and Qwen misread the same way ("2615" -> 2645,
# "2491" -> 249, "02" -> 62). Rule B could not catch the third (its neighbour "01" has the same date).
# G. A third reader from another model family, Gemma 4 E4B (ollama, gemma4:e4b, greedy, thinking off),
#    reads a tight crop of the "Số: …" line (num.png: the line found by vision_boxes.swift, cut from
#    the full-resolution header; third_reader.py). Every v9 accept whose number comes from page 1
#    (where "page1" or "passed") is kept only if Gemma's leading number equals the accepted number's
#    digits before the first "/" (third_reader.third_ok); with no crop, or no number in Gemma's read,
#    v10 abstains. Accepts from the authentication block are typed, not handwritten, and are kept as v9.
#    Rule B runs on v9's accepts first, as in v9; G only removes accepts.
def apply_g(where: str, num: str, crop: bool, gemma_text: str | None) -> bool:
    """Rule G: True when a v9 accept survives the third reader."""
    from third_reader import third_ok

    return where == "auth" or (crop and third_ok(num, gemma_text))


# --- v11 (written 2026-11-28 after the tenth batch; developed on batches 1-10, 4,226 documents) ---
# v10 met the certificate on batch 10 but missed coverage (64.8%). Of its 176 rejections, 90 have no
# page-1 date Vision can parse. Five changes, each found in batch 10's rejections and checked on 1-10:
# S. "Số" read as capitals and followed by a colon ("SỐ: 1324/QĐ-TTg"; not "QUYẾT ĐỊNH SỐ 963/QĐ-TTg" in
#    an issuer's name), or with a comma-below S ("Șố"), starts a number too.
# Y. The year segment is required for the types TT, NĐ, VBHN, TTLT and QHnn only, compared whole:
#    v6 compared prefixes, so the Prime Minister's letters ("884/TTg-CN") needed a year and failed.
# E. The e-signature window grows from 14 to 45 days when Vision reads the day as two digits ("04",
#    "30"): the error the 14 days guard against is a two-digit day read as one ("21" -> 2).
# P. Rule L also takes "thông qua tại phiên họp ngày …", the closing sentence of the resolutions of
#    the National Assembly Standing Committee (NQ-UBTVQH15), whose page 1 carries no date.
# F. When page 1's place-date line is damaged ("ngày 0 5 tháng 11", "tháng1 1", "tháng |1", "ngày//"),
#    its day and month are read with spaces dropped and "|" "/" "l" "I" "!" as 1, "O" "o" as 0; the
#    date is used only through accept11 (Qwen's date must equal it), with the 14-day window.
# Rules B (register order) and G (third reader) run on v11's accepts as in v10.
SO11_RE = re.compile(r"(?:S[ốôoóồổ6]|s[ốô]|Ș[ốô]|S[ỐÔ](?=\s*:))\s*[:.]?\s*")
PASSED11_RE = re.compile(
    r"thông\s*qua\s*(?:tại\s*phiên\s*họp\s*)?ngày\s*(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})", re.IGNORECASE
)
FDATE_RE = re.compile(r",\s*ngày([^,\n]{0,6}?)tháng([^,\n]{0,6}?)n[ăặắa]m([^,\n]{0,8})", re.IGNORECASE)
ONE11 = str.maketrans({"|": "1", "/": "1", "l": "1", "I": "1", "!": "1", "O": "0", "o": "0"})


def checks_pass11(num: str | None, d: tuple[int, int, int] | None) -> bool:
    """checks_pass6 with the type compared whole (rule Y)."""
    if not checks_pass(num, d):
        return False
    parts = num.split("/")  # type: ignore[union-attr]
    kind = parts[-1].split("-")[0]
    if kind == "VBHN" and len(parts) == 2:
        return len(parts[0]) <= 4
    has_year = len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[1]) is not None
    return has_year or not (kind in ("TT", "NĐ", "VBHN", "TTLT") or re.fullmatch(r"QH\d*", kind))


def emblem_ok11(text: str, d: tuple[int, int, int]) -> bool:
    """Rule E: 45 days when the place-date line writes the day with two digits, else 14."""
    m = DATE2_RE.search(DOTS.sub("", unicodedata.normalize("NFC", text)))
    return emblem_ok(text, d, EMBLEM_DAYS_L if m and len(m.group(1)) == 2 else EMBLEM_DAYS)


def passed_date11(text: str | None) -> tuple[int, int, int] | None:
    hits = PASSED11_RE.findall(DOTS.sub("", unicodedata.normalize("NFC", text or "")))
    return tuple(int(g) for g in hits[-1]) if hits else None  # type: ignore[return-value]


def read_date_f(text: str) -> tuple[int, int, int] | None:
    """Rule F: the place-date line with damaged digits, or None."""
    m = FDATE_RE.search(DOTS.sub("", unicodedata.normalize("NFC", text)))
    if not m:
        return None

    def part(s: str) -> int | None:
        s = re.sub(r"\s+", "", s).translate(ONE11)
        return int(s) if re.fullmatch(r"\d{1,2}", s) else None

    dd, mm = part(m.group(1)), part(m.group(2))
    y = re.match(r"\s*'?\s*(\d)\s*(\d)\s*(\d)\s*(\d)", m.group(3))
    return (dd, mm, int("".join(y.groups()))) if dd is not None and mm is not None and y else None


def accept11(
    text: str, q: str | None, vbhn_only: bool, d: tuple[int, int, int] | None, qd: tuple | None, window: str
) -> str | None:
    """accept9 with rules S and Y; window: "E" (rule E), "14" or "45" days."""
    if q is None or d is None or qd not in (d, (d[1], d[0], d[2])):
        return None
    if not (emblem_ok11(text, d) if window == "E" else emblem_ok(text, d, int(window))):
        return None
    cands = [n for n in read_numbers4(text, SO11_RE) if checks_pass11(n, d)]
    if len(cands) != 1:
        return None
    if vbhn_only and not cands[0].split("/")[-1].startswith("VBHN"):
        return None
    return merge9(cands[0], qwen_number(q, SO11_RE))


def read_v11(
    text: str, q: str | None, atext: str | None, aq: str | None, ptext: str | None, pq: str | None
) -> tuple[str | None, tuple | None, str]:
    """read_v9 with rules S, Y, E, P and F. where: "page1", "fuzzy", "auth", "passed" or ""."""
    qlines = [x.strip() for x in (q or "").splitlines() if x.strip()]
    qd = qwen_date(qlines[1] if len(qlines) > 1 else None)
    d = read_date2(text)
    n = accept11(text, q, False, d, qd, "E")
    if n:
        return n, d, "page1"
    if d is None and (fd := read_date_f(text)) is not None:
        n = accept11(text, q, False, fd, qd, "14")
        if n:
            return n, fd, "fuzzy"
    if atext is not None and aq is not None:
        alines = [x.strip() for x in aq.splitlines() if x.strip()]
        d2 = read_date2(atext)
        n2 = accept11(atext, aq, True, d2, qwen_date(alines[1] if len(alines) > 1 else None), "E")
        if n2:
            return n2, d2, "auth"
    if d is None and ptext is not None and pq is not None:
        d3 = passed_date11(ptext)
        n3 = accept11(text, q, False, d3, qwen_date(pq), str(EMBLEM_DAYS_L))
        if n3:
            return n3, d3, "passed"
    return None, d, ""


def seal_box(rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    """Bounding box of the largest blob of red ink, grown to take in the signer's title."""
    red = red_mask(rgb[::4, ::4])
    if red.mean() <= RED_PAGE:
        return None
    lab, n = ndimage.label(ndimage.binary_dilation(red, iterations=6))
    if not n:
        return None
    sizes = ndimage.sum(red, lab, range(1, n + 1))
    ys, xs = ndimage.find_objects(lab)[int(np.argmax(sizes))]
    y0, y1, x0, x1 = ys.start * 4, ys.stop * 4, xs.start * 4, xs.stop * 4
    h, w = y1 - y0, x1 - x0
    H, W = rgb.shape[:2]
    return max(0, x0 - w // 2), max(0, y0 - h // 2), min(W, x1 + w // 2), min(H, y1 + h // 3)


def prep(doc_id: int) -> dict:
    out = PRIV / "pages" / f"{doc_id:03d}"
    out.mkdir(parents=True, exist_ok=True)
    pdf = PRIV / "pdf" / f"{doc_id:03d}.pdf"
    jobs = f"{pdf}\t1\t{out / 'p1.png'}\n{pdf}\t0\t{out / 'plast.png'}\n"
    res = subprocess.run([str(RENDER)], input=jobs, text=True, capture_output=True).stdout.split()
    rec: dict = {"id": doc_id, "pages": None if "ERR" in res or len(res) < 4 else int(res[1])}
    if rec["pages"] is None:
        return rec
    try:
        from pypdf import PdfReader

        layer = PdfReader(pdf).pages[0].extract_text() or ""
        rec["text_layer"] = len(layer.strip()) > 50
        rec["layer_num"], rec["layer_date"] = read_number2(layer), read_date2(layer)
    except Exception:  # noqa: BLE001 - a broken text layer is just "no text layer"
        rec["text_layer"] = False
    p1 = Image.open(out / "p1.png").convert("RGB")
    p1.crop((0, 0, p1.width, int(p1.height * HEADER_SHARE))).save(out / "head.png")
    rec["head_red"] = dropout(str(out / "head.png"), str(out / "head_drop.png"))
    head = Image.open(out / "head.png")
    head.resize((1240, head.height * 1240 // head.width), Image.LANCZOS).save(out / "head_small.png")  # for Qwen
    try:  # v6: the VBHN authentication block, if the text layer has one
        loc = auth_locate(pdf)
    except Exception:  # noqa: BLE001 - no readable text layer, no block
        loc = None
    rec["auth"] = loc is not None
    if loc:
        page = out / "auth_page.png"
        subprocess.run([str(RENDER)], input=f"{pdf}\t{loc[0] + 1}\t{page}\n", text=True, capture_output=True)
        if page.exists():
            im = Image.open(page).convert("RGB")
            top, bot = max(0.0, loc[1] - AUTH_TOP), min(1.0, loc[1] + AUTH_BOTTOM)
            a = im.crop((0, int(im.height * top), im.width, int(im.height * bot)))
            a.save(out / "auth.png")
            a.resize((1240, a.height * 1240 // a.width), Image.LANCZOS).save(out / "auth_small.png")
        else:
            rec["auth"] = False
    try:  # v7: the same block, found with the tolerant locator; crops auth7.png / auth7_small.png
        loc7 = auth_locate7(pdf)
    except Exception:  # noqa: BLE001
        loc7 = None
    rec["auth7"] = loc7 is not None
    if loc7:
        page = out / "auth7_page.png"
        subprocess.run([str(RENDER)], input=f"{pdf}\t{loc7[0] + 1}\t{page}\n", text=True, capture_output=True)
        if page.exists():
            im = Image.open(page).convert("RGB")
            top, bot = max(0.0, loc7[1] - AUTH_TOP), min(1.0, loc7[1] + AUTH_BOTTOM)
            a = im.crop((0, int(im.height * top), im.width, int(im.height * bot)))
            a.save(out / "auth7.png")
            a.resize((1240, a.height * 1240 // a.width), Image.LANCZOS).save(out / "auth7_small.png")
        else:
            rec["auth7"] = False
    pl = Image.open(out / "plast.png")
    pl.resize((1240, pl.height * 1240 // pl.width), Image.LANCZOS).save(out / "plast_small.png")  # v9, Qwen
    last = np.asarray(pl.convert("RGB"))
    rec["last_red"] = float(red_mask(last[::4, ::4]).mean())
    box = seal_box(last)
    rec["seal"] = box is not None
    if box:
        Image.fromarray(last).crop(box).save(out / "seal.png")
        rec["seal_red"] = dropout(str(out / "seal.png"), str(out / "seal_drop.png"))
    return rec


def tesseract(path: str) -> str:
    env = {**os.environ, "TESSDATA_PREFIX": os.environ.get("TESSDATA_PREFIX", os.path.abspath("data/tessdata"))}
    r = subprocess.run(
        ["tesseract", path, "stdout", "-l", "vie", "--psm", "3"], capture_output=True, text=True, env=env
    )
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def has_title(text: str) -> bool:
    t = unicodedata.normalize("NFC", text).upper()
    return any(x in t for x in TITLES)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--md")
    ap.add_argument("--skip-ocr", action="store_true", help="reuse <VBCP_DIR>/ocr.json")
    ap.add_argument("--confirm", action="store_true", help="add the confirmation-batch verdicts of PREREG.md")
    ap.add_argument("--confirm3", action="store_true", help="add the third-batch (v3) verdicts of PREREG.md")
    ap.add_argument("--confirm4", action="store_true", help="add the fourth-batch (v4) verdicts of PREREG.md")
    ap.add_argument(
        "--to-adjudicate", action="store_true", help="list v4-accepted ids that differ from the listing (no values)"
    )
    ap.add_argument("--confirm5", action="store_true", help="add the fifth-batch (v5) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate5", action="store_true", help="v5-accepted ids that differ from the listing")
    ap.add_argument("--spot5", action="store_true", help="the 100 v5-accepted ids to read blind (PREREG)")
    ap.add_argument("--confirm6", action="store_true", help="add the sixth-batch (v6) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate6", action="store_true", help="v6-accepted ids that differ from the listing")
    ap.add_argument("--spot6", action="store_true", help="the 100 v6-accepted ids to read blind (PREREG)")
    ap.add_argument("--confirm7", action="store_true", help="add the seventh-batch (v7) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate7", action="store_true", help="v7-accepted ids that differ from the listing")
    ap.add_argument("--spot7", action="store_true", help="the 100 v7-accepted ids to read blind (PREREG)")
    ap.add_argument("--confirm8", action="store_true", help="add the eighth-batch (v8) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate8", action="store_true", help="v8-accepted ids that differ from the listing")
    ap.add_argument("--spot8", action="store_true", help="the 100 v8-accepted ids to read blind (PREREG)")
    ap.add_argument("--passed-paths", action="store_true", help="v9: last pages for Qwen with passed_prompt.txt")
    ap.add_argument("--confirm9", action="store_true", help="add the ninth-batch (v9) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate9", action="store_true", help="v9 or v8 accepts that differ from the listing")
    ap.add_argument("--spot9", action="store_true", help="the v9-accepted ids to read blind (PREREG)")
    ap.add_argument("--gemma-paths", action="store_true", help="v10: num.png of v9 page-1 accepts, for Gemma")
    ap.add_argument("--confirm10", action="store_true", help="add the tenth-batch (v10) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate10", action="store_true", help="v10 or v9 accepts that differ from the listing")
    ap.add_argument("--spot10", action="store_true", help="the v10-accepted ids to read blind (PREREG)")
    ap.add_argument("--gemma-paths11", action="store_true", help="v11: num.png of v9 or v11 page-1 accepts")
    ap.add_argument("--confirm11", action="store_true", help="add the eleventh-batch (v11) verdicts of PREREG.md")
    ap.add_argument("--to-adjudicate11", action="store_true", help="v11 or v9 accepts that differ from the listing")
    ap.add_argument("--spot11", action="store_true", help="the v11-accepted ids to read blind (PREREG)")
    args = ap.parse_args()
    listing = json.loads((PRIV / "docs.json").read_text(encoding="utf-8"))
    ids = sorted(int(p.stem) for p in (PRIV / "pdf").glob("*.pdf"))

    with Pool(8) as pool:
        recs = [r for r in pool.map(prep, ids) if r["pages"]]
    ocr_path = PRIV / "ocr.json"
    if args.skip_ocr and ocr_path.exists():
        ocr = json.loads(ocr_path.read_text(encoding="utf-8"))
    else:
        imgs = []
        for r in recs:
            d = PRIV / "pages" / f"{r['id']:03d}"
            imgs += [d / "head.png", d / "head_drop.png"] + ([d / "seal.png", d / "seal_drop.png"] if r["seal"] else [])
            imgs += [d / "auth.png"] if r.get("auth") else []
            imgs += [d / "auth7.png"] if r.get("auth7") else []
            imgs += [d / "plast.png"]  # v9, rule L
        run = subprocess.run(
            [str(VISION), "--jobs", "6"],
            input="".join(f"{p}\n" for p in imgs),
            text=True,
            capture_output=True,
            check=True,
        )
        ocr = {"V": {j["path"]: j["text"] for j in map(json.loads, run.stdout.splitlines())}}
        heads = [str(p) for p in imgs if p.name.startswith("head")]
        with Pool(8) as pool:
            ocr["T"] = dict(zip(heads, pool.map(tesseract, heads), strict=True))
        ocr_path.write_text(json.dumps(ocr, ensure_ascii=False), encoding="utf-8")

    qwen = {}
    if (PRIV / "qwen.jsonl").exists():  # vlm_ocr.py --prompt-file audits/real_scans/header_prompt.txt
        with open(PRIV / "qwen.jsonl", encoding="utf-8") as fh:
            qwen = {j["path"]: j["text"] for j in map(json.loads, fh)}
    qfull = {}
    if (PRIV / "qwen_full.jsonl").exists():  # same prompt on the full-resolution head.png, v4 rejections only
        with open(PRIV / "qwen_full.jsonl", encoding="utf-8") as fh:
            qfull = {j["path"]: j["text"] for j in map(json.loads, fh)}
    qauth = {}
    if (PRIV / "qwen_auth.jsonl").exists():  # same prompt on auth_small.png, the VBHN authentication block (v6)
        with open(PRIV / "qwen_auth.jsonl", encoding="utf-8") as fh:
            qauth = {j["path"]: j["text"] for j in map(json.loads, fh)}
    qauth7 = {}
    if (PRIV / "qwen_auth7.jsonl").exists():  # same prompt on auth7_small.png, the v7-located block
        with open(PRIV / "qwen_auth7.jsonl", encoding="utf-8") as fh:
            qauth7 = {j["path"]: j["text"] for j in map(json.loads, fh)}
    qpassed = {}
    if (PRIV / "qwen_passed.jsonl").exists():  # passed_prompt.txt on plast_small.png (v9, rule L)
        with open(PRIV / "qwen_passed.jsonl", encoding="utf-8") as fh:
            qpassed = {j["path"]: j["text"] for j in map(json.loads, fh)}
    gemma = {}
    if (PRIV / "gemma_num.jsonl").exists():  # third_reader.py read: Gemma on num.png (v10, rule G)
        with open(PRIV / "gemma_num.jsonl", encoding="utf-8") as fh:
            gemma = {j["path"]: j["text"] for j in map(json.loads, fh)}
    if args.passed_paths:  # page 1 gives no date and Vision finds the closing sentence on the last page
        for r in recs:
            d = PRIV / "pages" / f"{r['id']:03d}"
            if read_date2(ocr["V"].get(str(d / "head.png"), "")) is None and passed_date11(
                ocr["V"].get(str(d / "plast.png"))
            ):  # v11 (rule P): a superset of v9's pages
                print(d / "plast_small.png")
        return
    adj = (
        json.loads((PRIV / "adjudication.json").read_text(encoding="utf-8"))
        if (PRIV / "adjudication.json").exists()
        else {}
    )
    rows = []
    for r in recs:
        d = PRIV / "pages" / f"{r['id']:03d}"
        truth = listing[r["id"]]
        tn = canon(truth["number"])
        td = tuple(int(x) for x in truth["date"].split("/"))
        row = {
            "id": r["id"],
            "kind": tn.split("/")[-1].split("-")[0],
            "tail": tn.split("/")[-1],
            "scan": not r["text_layer"],
            "r": r,
        }
        for e in ("V", "T"):
            for v in ("raw", "drop"):
                text = ocr[e].get(str(d / ("head.png" if v == "raw" else "head_drop.png")), "")
                num, dt = read_number(text), read_date(text)
                row[e, v] = {
                    "num": num,
                    "date": dt,
                    "num_ok": num == tn,
                    "date_ok": dt == td,
                    "pass": checks_pass(num, dt),
                }
                num, dt = read_number2(text), read_date2(text)
                row[e, v + "2"] = {
                    "num": num,
                    "date": dt,
                    "num_ok": num == tn,
                    "date_ok": dt == td,
                    "pass": checks_pass(num, dt),
                }
        text = ocr["V"].get(str(d / "head.png"), "")
        num, dt = read_number3(text), read_date2(text)
        q = qwen.get(str(d / "head_small.png"))
        qn, qd = read_qwen(q) if q is not None else (None, None)
        row["v3"] = {
            "num": num,
            "date": dt,
            "num_ok": num == tn,
            "date_ok": dt == td,
            "rules": checks_pass3(num, dt),
            "qwen": q is not None,
            "agree": q is not None and qn == num and qd == dt,
        }
        n1, d4 = read_v4(text, [q] if q is not None else [])
        f = qfull.get(str(d / "head.png"))
        n2 = read_v4(text, [f])[0] if n1 is None and f is not None else None
        page = adj.get(str(r["id"]), {})
        pn = truth4(page.get("number", truth["number"]))
        pd = tuple(int(x) for x in page.get("date", truth["date"]).split("/"))
        row["v4"] = {
            "num": n1 or n2,
            "date": d4,
            "stage": 1 if n1 else (2 if n2 else 0),
            "full": f is not None,
            "ok_listing": (n1 or n2, d4) == (truth4(truth["number"]), td),
            "ok_page": (n1 or n2, d4) == (pn, pd),
            "adjudicated": bool(page),
        }
        n5, d5 = read_v5(text, [q] if q is not None else [])
        row["v5"] = {
            "num": n5,
            "date": d5,
            "ok_listing": (n5, d5) == (truth4(truth["number"]), td),
            "ok_page": (n5, d5) == (pn, pd),
            "adjudicated": bool(page),
        }
        # Where v6 finds a block, its crop is the v7 crop pixel for pixel (125 of 125 in batches 4-6), so
        # from batch 7 on v6 reuses the v7 reads instead of a second Qwen run on the same image.
        at = ocr["V"].get(str(d / "auth.png"), ocr["V"].get(str(d / "auth7.png"))) if r.get("auth") else None
        aq = qauth.get(str(d / "auth_small.png"), qauth7.get(str(d / "auth7_small.png"))) if r.get("auth") else None
        n6, d6, where = read_v6(text, q, at, aq)
        row["v6"] = {
            "num": n6,
            "date": d6,
            "where": where,
            "auth": bool(r.get("auth")),
            "auth_qwen": aq is not None,
            "ok_listing": (n6, d6) == (truth4(truth["number"]), td),
            "ok_page": (n6, d6) == (pn, pd),
            "adjudicated": bool(page),
        }
        at7 = ocr["V"].get(str(d / "auth7.png")) if r.get("auth7") else None
        aq7 = qauth7.get(str(d / "auth7_small.png")) if r.get("auth7") else None
        n7, d7, where7 = read_v6(text, q, at7, aq7)  # v7 = v6 rule, v7 locator
        row["v7"] = {
            "num": n7,
            "date": d7,
            "where": where7,
            "auth": bool(r.get("auth7")),
            "auth_qwen": aq7 is not None,
            "ok_listing": (n7, d7) == (truth4(truth["number"]), td),
            "ok_page": (n7, d7) == (pn, pd),
            "adjudicated": bool(page),
        }
        n8, d8, where8 = read_v8(text, q, at7, aq7)  # rule B below, once every document is read
        row["v8"] = {
            "num": n8,
            "date": d8,
            "where": where8,
            "register": False,
            "auth": bool(r.get("auth7")),
            "auth_qwen": aq7 is not None,
            "ok_listing": (n8, d8) == (truth4(truth["number"]), td),
            "ok_page": (n8, d8) == (pn, pd),
            "adjudicated": bool(page),
        }
        pt = ocr["V"].get(str(d / "plast.png"))
        pq = qpassed.get(str(d / "plast_small.png"))
        n9, d9, where9 = read_v9(text, q, at7, aq7, pt, pq)  # rule B (register_drop9) below
        row["v9"] = {
            "num": n9,
            "date": d9,
            "where": where9,
            "register": False,
            "auth": bool(r.get("auth7")),
            "auth_qwen": aq7 is not None,
            "passed": read_date2(text) is None and passed_date(pt) is not None,
            "passed_qwen": pq is not None,
            "ok_listing": (n9, d9) == (truth4(truth["number"]), td),
            "ok_page": (n9, d9) == (pn, pd),
            "adjudicated": bool(page),
        }
        crop = (d / "num.png").exists()
        row["v10"] = {
            **row["v9"],
            "crop": crop,
            "gemma": gemma.get(str(d / "num.png")),
            "gemma_read": str(d / "num.png") in gemma,
            "veto": False,
        }
        n11, d11, where11 = read_v11(text, q, at7, aq7, pt, pq)  # rules B and G below
        row["v11"] = {
            "num": n11,
            "date": d11,
            "where": where11,
            "register": False,
            "crop": crop,
            "gemma": row["v10"]["gemma"],
            "veto": False,
            "passed": read_date2(text) is None and passed_date11(pt) is not None,
            "passed_qwen": pq is not None,
            "ok_listing": (n11, d11) == (truth4(truth["number"]), td),
            "ok_page": (n11, d11) == (pn, pd),
            "adjudicated": bool(page),
        }
        row["layer"] = {"num": r.get("layer_num"), "date": r.get("layer_date")}
        row["layer"]["num_ok"] = row["layer"]["num"] == tn
        row["layer"]["date_ok"] = tuple(row["layer"]["date"] or ()) == td
        if r["seal"]:
            row["title"] = {
                v: has_title(ocr["V"].get(str(d / f"seal{s}.png"), "")) for v, s in (("raw", ""), ("drop", "_drop"))
            }
        rows.append(row)
    dropped = register_drop([(x["id"], x["v8"]["num"], x["v8"]["date"]) for x in rows if x["v8"]["num"]])
    for x in rows:
        if x["id"] in dropped:  # the read stays in "register_num" for the report; the document is not accepted
            x["v8"].update(num=None, register=True, register_num=x["v8"]["num"])
    dropped9 = register_drop9([(x["id"], x["v9"]["num"], x["v9"]["date"]) for x in rows if x["v9"]["num"]])
    for x in rows:
        if x["id"] in dropped9:
            x["v9"].update(num=None, register=True, register_num=x["v9"]["num"])
            x["v10"].update(num=None, register=True, register_num=x["v10"]["num"])
    dropped11 = register_drop9([(x["id"], x["v11"]["num"], x["v11"]["date"]) for x in rows if x["v11"]["num"]])
    for x in rows:
        if x["id"] in dropped11:
            x["v11"].update(num=None, register=True, register_num=x["v11"]["num"])
    for x in rows:  # rule G, after rule B
        for k in ("v10", "v11"):
            v = x[k]
            if v["num"] and not apply_g(v["where"], v["num"], v["crop"], v["gemma"]):
                v.update(num=None, veto=True, veto_num=v["num"])
    (PRIV / "scan_rows.json").write_text(
        json.dumps(
            [{**{k if isinstance(k, str) else "_".join(k): v for k, v in x.items()}} for x in rows],
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    if args.to_adjudicate:  # ids only: the reader looks at the page without seeing any engine's read
        print(" ".join(str(x["id"]) for x in rows if x["v4"]["stage"] and not x["v4"]["ok_listing"]))
        return
    if args.to_adjudicate5:  # v5 accepts that differ from the listing, ids only
        print(" ".join(str(x["id"]) for x in rows if x["v5"]["num"] and not x["v5"]["ok_listing"]))
        return
    if args.spot5:  # PREREG "Fifth batch": 100 v5 accepts that agree with the listing, ids only
        agree = sorted(x["id"] for x in rows if x["v5"]["num"] and x["v5"]["ok_listing"])
        print(" ".join(map(str, random.Random(SPOT_SEED).sample(agree, min(SPOT_N, len(agree))))))
        return
    if args.to_adjudicate6:  # v6 accepts that differ from the listing, ids only
        print(" ".join(str(x["id"]) for x in rows if x["v6"]["num"] and not x["v6"]["ok_listing"]))
        return
    if args.spot6:  # PREREG "Sixth batch": 100 v6 accepts that agree with the listing, ids and where read
        agree = sorted(x["id"] for x in rows if x["v6"]["num"] and x["v6"]["ok_listing"])
        where = {x["id"]: x["v6"]["where"] for x in rows}
        print(" ".join(f"{i}:{where[i]}" for i in random.Random(SPOT_SEED6).sample(agree, min(SPOT_N, len(agree)))))
        return
    if args.to_adjudicate7:  # v7 accepts that differ from the listing, ids only
        print(" ".join(str(x["id"]) for x in rows if x["v7"]["num"] and not x["v7"]["ok_listing"]))
        return
    if args.spot7:  # PREREG "Seventh batch": every agreeing accept from the block, and 100 random from page 1
        agree = sorted(x["id"] for x in rows if x["v7"]["num"] and x["v7"]["ok_listing"])
        where = {x["id"]: x["v7"]["where"] for x in rows}
        auth = [i for i in agree if where[i] == "auth"]
        page1 = [i for i in agree if where[i] == "page1"]
        pick = auth + random.Random(SPOT_SEED7).sample(page1, min(SPOT_N, len(page1)))
        print(" ".join(f"{i}:{where[i]}" for i in pick))
        return
    if args.to_adjudicate8:  # v8 accepts that differ from the listing, ids only
        print(" ".join(str(x["id"]) for x in rows if x["v8"]["num"] and not x["v8"]["ok_listing"]))
        return
    if args.spot8:  # PREREG "Eighth batch": every agreeing accept from the block, and 100 random from page 1
        agree = sorted(x["id"] for x in rows if x["v8"]["num"] and x["v8"]["ok_listing"])
        where = {x["id"]: x["v8"]["where"] for x in rows}
        auth = [i for i in agree if where[i] == "auth"]
        page1 = [i for i in agree if where[i] == "page1"]
        pick = auth + random.Random(SPOT_SEED8).sample(page1, min(SPOT_N, len(page1)))
        print(" ".join(f"{i}:{where[i]}" for i in pick))
        return
    if args.to_adjudicate9:  # v9 or v8 accepts that differ from the listing, ids only
        print(" ".join(str(x["id"]) for x in rows if any(x[k]["num"] and not x[k]["ok_listing"] for k in ("v9", "v8"))))
        return
    if args.spot9:  # PREREG "Ninth batch": every agreeing accept from the block or the last page, 100 from page 1
        agree = sorted(x["id"] for x in rows if x["v9"]["num"] and x["v9"]["ok_listing"])
        where = {x["id"]: x["v9"]["where"] for x in rows}
        rest = [i for i in agree if where[i] in ("auth", "passed")]
        page1 = [i for i in agree if where[i] == "page1"]
        pick = rest + random.Random(SPOT_SEED9).sample(page1, min(SPOT_N, len(page1)))
        print(" ".join(f"{i}:{where[i]}" for i in pick))
        return
    if args.gemma_paths:  # PREREG "Tenth batch": Gemma reads the number line of every v9 page-1 accept
        for x in rows:
            if x["v9"]["num"] and x["v9"]["where"] != "auth" and x["v10"]["crop"]:
                print(PRIV / "pages" / f"{x['id']:03d}" / "num.png")
        return
    if args.to_adjudicate10:  # v10's accepts are v9's minus rule G, so v9's cover both
        print(" ".join(str(x["id"]) for x in rows if x["v9"]["num"] and not x["v9"]["ok_listing"]))
        return
    if args.spot10:  # PREREG "Tenth batch": every agreeing accept from the block or the last page, 100 from page 1
        agree = sorted(x["id"] for x in rows if x["v10"]["num"] and x["v10"]["ok_listing"])
        where = {x["id"]: x["v10"]["where"] for x in rows}
        rest = [i for i in agree if where[i] in ("auth", "passed")]
        page1 = [i for i in agree if where[i] == "page1"]
        pick = rest + random.Random(SPOT_SEED10).sample(page1, min(SPOT_N, len(page1)))
        print(" ".join(f"{i}:{where[i]}" for i in pick))
        return
    if args.gemma_paths11:  # PREREG "Eleventh batch": the number line of every v9 or v11 page-1 accept
        # rule G has already run on rows, so a v11 read with no Gemma read yet sits in "veto_num": batch 11's
        # first list missed every such read (40 of them), and Gemma read only v9's 344 crops.
        for x in rows:
            if x["v10"]["crop"] and any(
                (x[k]["num"] or x[k].get("register_num") or x[k].get("veto_num")) and x[k]["where"] != "auth"
                for k in ("v9", "v11")
            ):
                print(PRIV / "pages" / f"{x['id']:03d}" / "num.png")
        return
    if args.to_adjudicate11:  # v11 or v9 accepts (v10's are a subset of v9's) that differ from the listing
        print(
            " ".join(str(x["id"]) for x in rows if any(x[k]["num"] and not x[k]["ok_listing"] for k in ("v11", "v9")))
        )
        return
    if args.spot11:  # PREREG "Eleventh batch": every agreeing accept not from page 1's clean date, 100 from page 1
        agree = sorted(x["id"] for x in rows if x["v11"]["num"] and x["v11"]["ok_listing"])
        where = {x["id"]: x["v11"]["where"] for x in rows}
        rest = [i for i in agree if where[i] in ("auth", "passed", "fuzzy")]
        page1 = [i for i in agree if where[i] == "page1"]
        pick = rest + random.Random(SPOT_SEED11).sample(page1, min(SPOT_N, len(page1)))
        print(" ".join(f"{i}:{where[i]}" for i in pick))
        return
    text = report(rows) + (confirm(rows) if args.confirm else []) + (confirm3(rows) if args.confirm3 else [])
    text += confirm4(rows) if args.confirm4 else []
    text += confirm5(rows) if args.confirm5 else []
    text += confirm6(rows) if args.confirm6 else []
    text += confirm7(rows) if args.confirm7 else []
    text += confirm8(rows) if args.confirm8 else []
    text += confirm9(rows) if args.confirm9 else []
    text += confirm10(rows) if args.confirm10 else []
    text += confirm11(rows) if args.confirm11 else []
    print("\n".join(text))
    if args.md:
        Path(args.md).write_text("\n".join(text) + "\n", encoding="utf-8")


ALPHA, DELTA = 0.01, 0.1  # as audits/ocr_pilot/analyze.py


def confirm(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Confirmation batch", on this batch alone."""
    n = len(rows)
    acc = [x["V", "raw2"] for x in rows if x["V", "raw2"]["pass"]]
    wrong = sum(not (a["num_ok"] and a["date_ok"]) for a in acc)
    ub = cp_upper(wrong, len(acc)) if acc else 1.0
    v1 = "GO" if ub <= 0.03 else ("KILL v2" if ub > 0.05 else "ITERATE")
    num = sum(x["V", "raw"]["num_ok"] for x in rows) / n
    dat = sum(x["V", "raw"]["date_ok"] for x in rows) / n
    v2 = "GO" if num >= 0.95 and dat >= 0.95 else ("ITERATE" if min(num, dat) >= 0.80 else "RETHINK")
    p = binom_cdf(wrong, len(acc), ALPHA) if acc else 1.0
    cert = len(acc) >= 230 and p <= DELTA
    return [
        "",
        "## 6. Confirmation batch: pre-registered verdicts",
        "",
        'PREREG.md, "Confirmation batch": parser v2 frozen at commit a0bdc77, documents not seen before.',
        "",
        f"1. Primary (Vision, as scanned, v2): {len(acc)} of {n} accepted, {wrong} wrong, 95% upper bound "
        f"{pct(ub)} → **{v1}**.",
        f"2. Replication of §1 (v1 parser): number {pct(num)}, date {pct(dat)} → **{v2}**.",
        f"3. Certificate at α = {pct(ALPHA)}, δ = {DELTA}: {len(acc)} accepted, binomial p = {p:.3f} → "
        + (
            "**certified**."
            if cert
            else "**not certified**" + (" (fewer than 230 accepted)." if len(acc) < 230 else ".")
        ),
    ]


def confirm3(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Third batch (v3)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    if missing:  # a missing second read would count as a rejection and inflate safety
        raise SystemExit(f"no Qwen read for {len(missing)} documents (first: {missing[:5]}); run vlm_ocr.py first")
    n = len(rows)
    ok = [x["v3"]["num_ok"] and x["v3"]["date_ok"] for x in rows]
    acc = [i for i, x in enumerate(rows) if x["v3"]["rules"] and x["v3"]["agree"]]
    wrong = sum(not ok[i] for i in acc)
    ub = cp_upper(wrong, len(acc)) if acc else 1.0
    v1 = "GO" if ub <= 0.03 else ("KILL v3" if ub > 0.05 else "ITERATE")
    cov = len(acc) / n
    p = binom_cdf(wrong, len(acc), ALPHA) if acc else 1.0
    cert = len(acc) >= 230 and p <= DELTA
    rul = [i for i, x in enumerate(rows) if x["v3"]["rules"]]
    rw = sum(not ok[i] for i in rul)
    lost = sum(ok[i] for i in rul if i not in set(acc))
    scans = [i for i, x in enumerate(rows) if x["scan"]]
    acc_s = [i for i in acc if rows[i]["scan"]]
    return [
        "",
        "## 7. Third batch: pre-registered verdicts for v3",
        "",
        'PREREG.md, "Third batch (v3)": v3 frozen at the commit that added that section, documents not seen',
        "before. v3 accepts a document when Vision's read passes `checks_pass3` and Qwen3.5-4B's read of the",
        "same header (1240 px wide, `header_prompt.txt`) gives the same number and date.",
        "",
        f"1. Primary (v3, rules + agreement): {len(acc)} of {n} accepted, {wrong} wrong, 95% upper bound "
        f"{pct(ub)} → **{v1}**.",
        f"2. Coverage: {pct(cov)} (bar ≥ 70%) → **{'met' if cov >= 0.70 else 'missed'}**. "
        f"Scans: {len(acc_s)} of {len(scans)} accepted.",
        f"3. Certificate at α = {pct(ALPHA)}, δ = {DELTA}: {len(acc)} accepted, binomial p = {p:.3f} → "
        + (
            "**certified**."
            if cert
            else "**not certified**" + (" (fewer than 230 accepted)." if len(acc) < 230 else ".")
        ),
        f"4. Report only: rules without Qwen accept {len(rul)}, {rw} wrong (upper bound "
        f"{pct(cp_upper(rw, len(rul)) if rul else 1.0)}). Qwen's disagreement rejects {lost} documents that "
        "Vision read correctly.",
    ]


def confirm4(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Fourth batch (v4)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} documents (first: {missing[:5]}); run vlm_ocr.py first")
    no_full = [x["id"] for x in rows if x["v4"]["stage"] != 1 and x["v4"]["date"] and not x["v4"]["full"]]
    n = len(rows)
    acc = [x["v4"] for x in rows if x["v4"]["stage"]]
    acc1 = [a for a in acc if a["stage"] == 1]
    out = ["", "## 8. Fourth batch: pre-registered verdicts for v4", ""]
    out += [
        'PREREG.md, "Fourth batch (v4)": v4 frozen at the commit that added that section, documents not seen',
        "before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected an accepted document that disagrees with it (`adjudication.json`).",
        "",
    ]
    if no_full:
        out.append(f"Report-only row: {len(no_full)} rejections have no full-resolution Qwen read.")
    for name, a in (("Primary, v4", acc1), ("Report only, v4 + full-resolution re-read of rejections", acc)):
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else ("KILL v4" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(len(a) / n)}), {w} wrong against the page, 95% upper "
            f"bound {pct(ub)} → **{verdict}**; certificate at α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → "
            f"**{'certified' if cert else 'not certified'}**."
        )
    wl = sum(not x["ok_listing"] for x in acc)
    out.append(
        f"- Against the listing as published: {wl} wrong of {len(acc)}; "
        f"{sum(x['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


SPOT_SEED, SPOT_N = 20261127, 100
SPOT_SEED6 = 20261128
SPOT_SEED7 = 20261129
SPOT_SEED8 = 20261130
SPOT_SEED9 = 20261201
SPOT_SEED10 = 20261202
SPOT_SEED11 = 20261203


def confirm5(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Fifth batch (v5)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} documents (first: {missing[:5]}); run vlm_ocr.py first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 9. Fifth batch: pre-registered verdicts for v5", ""]
    out += [
        'PREREG.md, "Fifth batch (v5)": v5 frozen at the commit that added that section, documents not seen',
        "before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} random accepted documents that agree with it.",
        "",
    ]
    for name, key in (("Primary, v5", "v5"), ("Report only, v4", "v4")):
        a = [x[key] for x in rows if x[key]["num"] and (key == "v5" or x[key]["stage"] == 1)]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, bar 70% → {'met' if cov >= 0.7 else 'missed'}), "
            f"{w} wrong against the page, 95% upper bound {pct(ub)} → **{verdict}**; certificate at "
            f"α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → **{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v5"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
    ):
        ga = [x for x in g if x["v5"]["num"]]
        out.append(
            f"- v5 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v5']['ok_page'] for x in ga)} wrong against the page."
        )
    out.append(
        f"- Against the listing as published: {sum(not x['v5']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v5']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def confirm6(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Sixth batch (v6)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    missing += [x["id"] for x in rows if x["v6"]["auth"] and not x["v6"]["auth_qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} crops (first: {missing[:5]}); run vlm_ocr.py first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 10. Sixth batch: pre-registered verdicts for v6", ""]
    out += [
        'PREREG.md, "Sixth batch (v6)": v6 frozen at the commit that added that section, documents not seen',
        "before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} random accepted documents that agree with it.",
        "",
    ]
    for name, key in (("Primary, v6", "v6"), ("Report only, v5", "v5")):
        a = [x[key] for x in rows if x[key]["num"]]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, bar 70% → {'met' if cov >= 0.7 else 'missed'}), "
            f"{w} wrong against the page, 95% upper bound {pct(ub)} → **{verdict}**; certificate at "
            f"α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → **{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v6"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
        ("VBHN (listing)", [x for x in rows if x["kind"] == "VBHN"]),
        ("not VBHN (listing)", [x for x in rows if x["kind"] != "VBHN"]),
    ):
        ga = [x for x in g if x["v6"]["num"]]
        out.append(
            f"- v6 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v6']['ok_page'] for x in ga)} wrong against the page."
        )
    au = [x for x in acc if x["v6"]["where"] == "auth"]
    out.append(
        f"- Accepted from the authentication block: {len(au)} (block found in {sum(x['v6']['auth'] for x in rows)} "
        f"PDFs), {sum(not x['v6']['ok_page'] for x in au)} wrong against the page."
    )
    out.append(
        f"- Against the listing as published: {sum(not x['v6']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v6']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def confirm7(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Seventh batch (v7)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    missing += [x["id"] for x in rows if x["v7"]["auth"] and not x["v7"]["auth_qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} crops (first: {missing[:5]}); run vlm_ocr.py first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 11. Seventh batch: pre-registered verdicts for v7", ""]
    out += [
        'PREREG.md, "Seventh batch (v7)": v7 frozen at the commit that added that section, documents not seen',
        "before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} accepted documents that agree with it: every",
        "one accepted from the authentication block, and 100 random ones accepted from page 1.",
        "",
    ]
    for name, key in (("Primary, v7", "v7"), ("Report only, v6", "v6"), ("Report only, v5", "v5")):
        a = [x[key] for x in rows if x[key]["num"]]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, bar 70% → {'met' if cov >= 0.7 else 'missed'}), "
            f"{w} wrong against the page, 95% upper bound {pct(ub)} → **{verdict}**; certificate at "
            f"α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → **{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v7"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
        ("VBHN (listing)", [x for x in rows if x["kind"] == "VBHN"]),
        ("not VBHN (listing)", [x for x in rows if x["kind"] != "VBHN"]),
    ):
        ga = [x for x in g if x["v7"]["num"]]
        out.append(
            f"- v7 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v7']['ok_page'] for x in ga)} wrong against the page."
        )
    au = [x for x in acc if x["v7"]["where"] == "auth"]
    out.append(
        f"- Accepted from the authentication block: {len(au)} (block found in {sum(x['v7']['auth'] for x in rows)} "
        f"PDFs), {sum(not x['v7']['ok_page'] for x in au)} wrong against the page."
    )
    out.append(
        f"- Against the listing as published: {sum(not x['v7']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v7']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def confirm8(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Eighth batch (v8)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    missing += [x["id"] for x in rows if x["v8"]["auth"] and not x["v8"]["auth_qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} crops (first: {missing[:5]}); run vlm_ocr.py first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 12. Eighth batch: pre-registered verdicts for v8", ""]
    out += [
        'PREREG.md, "Eighth batch (v8)": v8 frozen at the commit that added that section, documents not seen',
        "before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} accepted documents that agree with it: every",
        "one accepted from the authentication block, and 100 random ones accepted from page 1.",
        "",
    ]
    for name, key in (("Primary, v8", "v8"), ("Report only, v7", "v7")):
        a = [x[key] for x in rows if x[key]["num"]]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, bar 70% → {'met' if cov >= 0.7 else 'missed'}), "
            f"{w} wrong against the page, 95% upper bound {pct(ub)} → **{verdict}**; certificate at "
            f"α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → **{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v8"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
        ("VBHN (listing)", [x for x in rows if x["kind"] == "VBHN"]),
        ("not VBHN (listing)", [x for x in rows if x["kind"] != "VBHN"]),
    ):
        ga = [x for x in g if x["v8"]["num"]]
        out.append(
            f"- v8 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v8']['ok_page'] for x in ga)} wrong against the page."
        )
    lost = [x for x in rows if x["v7"]["num"] and not x["v8"]["num"]]
    reg = [x for x in lost if x["v8"]["register"]]
    amb = [x for x in lost if not x["v8"]["register"]]
    for lab, g in (("rule A (more than one candidate)", amb), ("rule B (register order)", reg)):
        out.append(
            f"- v7 accepts dropped by {lab}: {len(g)}, of which {sum(not x['v7']['ok_page'] for x in g)} "
            "wrong against the page."
        )
    au = [x for x in acc if x["v8"]["where"] == "auth"]
    out.append(
        f"- Accepted from the authentication block: {len(au)} (block found in {sum(x['v8']['auth'] for x in rows)} "
        f"PDFs), {sum(not x['v8']['ok_page'] for x in au)} wrong against the page."
    )
    out.append(
        f"- Against the listing as published: {sum(not x['v8']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v8']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def confirm9(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Ninth batch (v9)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    missing += [x["id"] for x in rows if x["v9"]["auth"] and not x["v9"]["auth_qwen"]]
    missing += [x["id"] for x in rows if x["v9"]["passed"] and not x["v9"]["passed_qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} crops (first: {missing[:5]}); run vlm_ocr.py first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 13. Ninth batch: pre-registered verdicts for v9", ""]
    out += [
        'PREREG.md, "Ninth batch (v9)": v9 frozen at the commit that added that section, documents not seen',
        "before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} accepted documents that agree with it: every",
        "one accepted from the authentication block or the last page, and 100 random ones from page 1.",
        "",
    ]
    for name, key in (("Primary, v9", "v9"), ("Report only, v8", "v8")):
        a = [x[key] for x in rows if x[key]["num"]]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, bar 70% → {'met' if cov >= 0.7 else 'missed'}), "
            f"{w} wrong against the page, 95% upper bound {pct(ub)} → **{verdict}**; certificate at "
            f"α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → **{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v9"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
        ("VBHN (listing)", [x for x in rows if x["kind"] == "VBHN"]),
        ("laws and resolutions of the National Assembly (listing)", [x for x in rows if "QH" in x["kind"]]),
        ("everything else (listing)", [x for x in rows if x["kind"] != "VBHN" and "QH" not in x["kind"]]),
    ):
        ga = [x for x in g if x["v9"]["num"]]
        out.append(
            f"- v9 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v9']['ok_page'] for x in ga)} wrong against the page."
        )
    for lab, where in (("the authentication block", "auth"), ("the last page (rule L)", "passed")):
        g = [x for x in acc if x["v9"]["where"] == where]
        out.append(f"- Accepted from {lab}: {len(g)}, {sum(not x['v9']['ok_page'] for x in g)} wrong against the page.")
    out.append(
        f"- Last pages with the closing sentence where page 1 has no date: {sum(x['v9']['passed'] for x in rows)}."
    )
    gain = [x for x in acc if not x["v8"]["num"]]
    lost = [x for x in rows if x["v8"]["num"] and not x["v9"]["num"]]
    out.append(
        f"- v9 accepts that v8 rejected: {len(gain)}, {sum(not x['v9']['ok_page'] for x in gain)} wrong against "
        f"the page; v8 accepts that v9 rejects: {len(lost)}, {sum(not x['v8']['ok_page'] for x in lost)} wrong."
    )
    reg = [x for x in rows if x["v9"]["register"]]
    regv8 = [x for x in rows if x["v8"]["register"]]
    out.append(
        f"- Dropped by rule B (ok_page is scored on the read before the drop): v9 {len(reg)}, of which "
        f"{sum(not x['v9']['ok_page'] for x in reg)} wrong against the page; v8 {len(regv8)}, of which "
        f"{sum(not x['v8']['ok_page'] for x in regv8)} wrong."
    )
    out.append(
        f"- Against the listing as published: {sum(not x['v9']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v9']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def confirm10(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Tenth batch (v10)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    missing += [x["id"] for x in rows if x["v9"]["auth"] and not x["v9"]["auth_qwen"]]
    missing += [x["id"] for x in rows if x["v9"]["passed"] and not x["v9"]["passed_qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} crops (first: {missing[:5]}); run vlm_ocr.py first")
    no_g = [
        x["id"]
        for x in rows
        if x["v9"]["num"] and x["v9"]["where"] != "auth" and x["v10"]["crop"] and not x["v10"]["gemma_read"]
    ]
    if no_g:
        raise SystemExit(f"no Gemma read for {len(no_g)} crops (first: {no_g[:5]}); run third_reader.py read first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 14. Tenth batch: pre-registered verdicts for v10", ""]
    out += [
        'PREREG.md, "Tenth batch (v10)": v10 frozen at the commit that added that section, documents not',
        "seen before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} accepted documents that agree with it: every",
        "one accepted from the authentication block or the last page, and 100 random ones from page 1.",
        "",
    ]
    for name, key in (("Primary, v10", "v10"), ("Report only, v9", "v9")):
        a = [x[key] for x in rows if x[key]["num"]]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, bar 70% → {'met' if cov >= 0.7 else 'missed'}), "
            f"{w} wrong against the page, 95% upper bound {pct(ub)} → **{verdict}**; certificate at "
            f"α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → **{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v10"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
        ("VBHN (listing)", [x for x in rows if x["kind"] == "VBHN"]),
        ("laws and resolutions of the National Assembly (listing)", [x for x in rows if "QH" in x["kind"]]),
        ("everything else (listing)", [x for x in rows if x["kind"] != "VBHN" and "QH" not in x["kind"]]),
    ):
        ga = [x for x in g if x["v10"]["num"]]
        out.append(
            f"- v10 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v10']['ok_page'] for x in ga)} wrong against the page."
        )
    veto = [x for x in rows if x["v10"]["veto"]]
    for lab, g in (
        ("no crop of the number line", [x for x in veto if not x["v10"]["crop"]]),
        ("Gemma read no number", [x for x in veto if x["v10"]["crop"] and lead_g(x) is None]),
        ("Gemma read another number", [x for x in veto if x["v10"]["crop"] and lead_g(x) is not None]),
    ):
        out.append(
            f"- v9 accepts removed by rule G, {lab}: {len(g)}, of which "
            f"{sum(not x['v9']['ok_page'] for x in g)} wrong against the page."
        )
    out.append(
        f"- Rule G in all: {len(veto)} removed, {sum(not x['v9']['ok_page'] for x in veto)} of them wrong; "
        f"v9 accepts kept by G that are wrong: {sum(not x['v10']['ok_page'] for x in acc)}."
    )
    for lab, where in (("the authentication block", "auth"), ("the last page (rule L)", "passed")):
        g = [x for x in acc if x["v10"]["where"] == where]
        out.append(
            f"- Accepted from {lab}: {len(g)}, {sum(not x['v10']['ok_page'] for x in g)} wrong against the page."
        )
    out.append(
        f"- Against the listing as published: {sum(not x['v10']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v10']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def confirm11(rows: list[dict]) -> list[str]:
    """Verdicts of PREREG.md, "Eleventh batch (v11)", on this batch alone."""
    missing = [x["id"] for x in rows if not x["v3"]["qwen"]]
    missing += [x["id"] for x in rows if x["v9"]["auth"] and not x["v9"]["auth_qwen"]]
    missing += [x["id"] for x in rows if x["v11"]["passed"] and not x["v11"]["passed_qwen"]]
    if missing:
        raise SystemExit(f"no Qwen read for {len(missing)} crops (first: {missing[:5]}); run vlm_ocr.py first")
    no_g = [
        x["id"]
        for x in rows
        if x["v10"]["crop"]
        and not x["v10"]["gemma_read"]
        # rule G has run by now: a read it removed sits in "veto_num". Batch 11's first scoring missed these
        # (Gemma had read only v9's 344 crops), and 40 v11 reads were removed for want of a Gemma read.
        and any(
            (x[k]["num"] or x[k].get("register_num") or x[k].get("veto_num")) and x[k]["where"] != "auth"
            for k in ("v9", "v11")
        )
    ]
    if no_g:
        raise SystemExit(f"no Gemma read for {len(no_g)} crops (first: {no_g[:5]}); run third_reader.py read first")
    spot = PRIV / "spot_check.json"
    if not spot.exists():
        raise SystemExit("no spot_check.json: the blind spot check is part of the truth (PREREG)")
    n_spot = sum(1 for k in json.loads(spot.read_text(encoding="utf-8")) if not k.startswith("_"))
    n = len(rows)
    out = ["", "## 15. Eleventh batch: pre-registered verdicts for v11", ""]
    out += [
        'PREREG.md, "Eleventh batch (v11)": v11 frozen at the commit that added that section, documents',
        "not seen before. Truth is the page: the listing, except where a reader who saw only the page image",
        "corrected it (`adjudication.json`): every accepted document that disagrees with the listing, and",
        f"the hidden errors found by a blind read of {n_spot} accepted documents that agree with it: every",
        "one accepted from the block, the last page or a damaged date line, and 100 random ones from page 1.",
        "",
    ]
    for name, key in (("Primary, v11", "v11"), ("Report only, v10", "v10")):
        a = [x[key] for x in rows if x[key]["num"]]
        w = sum(not x["ok_page"] for x in a)
        ub = cp_upper(w, len(a)) if a else 1.0
        p = binom_cdf(w, len(a), ALPHA) if a else 1.0
        verdict = "GO" if ub <= 0.03 else (f"KILL {key}" if ub > 0.05 else "ITERATE")
        cert = len(a) >= 230 and p <= DELTA
        cov = len(a) / n
        lo, hi = wilson(len(a), n)
        out.append(
            f"- {name}: {len(a)} of {n} accepted ({pct(cov)}, Wilson 95% {pct(lo)}–{pct(hi)}, bar 70% → "
            f"{'met' if cov >= 0.7 else 'missed'}), {w} wrong against the page, 95% upper bound {pct(ub)} → "
            f"**{verdict}**; certificate at α = {pct(ALPHA)}, δ = {DELTA}: p = {p:.3f} → "
            f"**{'certified' if cert else 'not certified'}**."
        )
    acc = [x for x in rows if x["v11"]["num"]]
    for lab, g in (
        ("scans", [x for x in rows if x["scan"]]),
        ("PDFs with a text layer", [x for x in rows if not x["scan"]]),
        ("VBHN (listing)", [x for x in rows if x["kind"] == "VBHN"]),
        ("laws and resolutions of the National Assembly (listing)", [x for x in rows if "QH" in x["kind"]]),
        ("resolutions of its Standing Committee (listing)", [x for x in rows if "UBTVQH" in x["tail"]]),
        ("everything else (listing)", [x for x in rows if x["kind"] != "VBHN" and "QH" not in x["kind"]]),
    ):
        ga = [x for x in g if x["v11"]["num"]]
        out.append(
            f"- v11 on {lab}: {len(ga)} of {len(g)} accepted ({pct(len(ga) / len(g)) if g else '—'}), "
            f"{sum(not x['v11']['ok_page'] for x in ga)} wrong against the page."
        )
    for lab, where in (
        ("page 1, date line parsed as before", "page1"),
        ("page 1, damaged date line (rule F)", "fuzzy"),
        ("the authentication block", "auth"),
        ("the last page (rules L and P)", "passed"),
    ):
        g = [x for x in acc if x["v11"]["where"] == where]
        out.append(
            f"- Accepted from {lab}: {len(g)}, {sum(not x['v11']['ok_page'] for x in g)} wrong against the page."
        )
    gain = [x for x in acc if not x["v10"]["num"]]
    lost = [x for x in rows if x["v10"]["num"] and not x["v11"]["num"]]
    out.append(
        f"- v11 accepts that v10 rejected: {len(gain)}, {sum(not x['v11']['ok_page'] for x in gain)} wrong; "
        f"v10 accepts that v11 rejects: {len(lost)}, {sum(not x['v10']['ok_page'] for x in lost)} wrong."
    )
    veto = [x for x in rows if x["v11"]["veto"]]
    reg = [x for x in rows if x["v11"]["register"]]
    out.append(
        f"- Removed by rule G: {len(veto)}, of which {sum(not x['v11']['ok_page'] for x in veto)} wrong; "
        f"by rule B: {len(reg)}, of which {sum(not x['v11']['ok_page'] for x in reg)} wrong "
        "(ok_page is scored on the read before the removal)."
    )
    out.append(
        f"- Against the listing as published: {sum(not x['v11']['ok_listing'] for x in acc)} wrong of {len(acc)}; "
        f"{sum(x['v11']['adjudicated'] for x in acc)} accepted documents were adjudicated."
    )
    return out


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / (1 + z * z / n)
    return c - h, c + h


def lead_g(x: dict) -> int | None:
    from third_reader import lead_number

    return lead_number(x["v10"]["gemma"])


def report(rows: list[dict]) -> list[str]:
    n = len(rows)
    scans = [x for x in rows if x["scan"]]
    out = [
        "# Real scans with real seals",
        "",
        f"Generated by `audits/real_scans/run_scans.py`. {n} documents from vanban.chinhphu.vn (the first",
        f"PDF of each, at most 5 MB); {len(scans)} have no text layer on page 1 (scans). Truth: the number and",
        "date in the listing. Thresholds: PREREG.md. Exact match = the value read equals the listing,",
        "spaces ignored.",
        "",
        "## 1. Number and date on page 1",
        "",
        "| Engine | Image | Set | Docs | Number exact | Date exact | Both |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for e, en in (("V", "Vision"), ("T", "Tesseract")):
        for v in ("raw", "drop"):
            for name, sub in (("all", rows), ("scans", scans)):
                if not sub:
                    continue
                k = len(sub)
                nk = sum(x[e, v]["num_ok"] for x in sub)
                dk = sum(x[e, v]["date_ok"] for x in sub)
                bk = sum(x[e, v]["num_ok"] and x[e, v]["date_ok"] for x in sub)
                out.append(f"| {en} | {v} | {name} | {k} | {pct(nk / k)} | {pct(dk / k)} | {pct(bk / k)} |")
    out += [
        "",
        "Vision as scanned, by document type:",
        "",
        "| Type | Docs | Number exact | Date exact |",
        "|---|---:|---:|---:|",
    ]
    kinds: dict[str, list] = {}
    for x in rows:
        kinds.setdefault(x["kind"], []).append(x)
    for kd, sub in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
        k = len(sub)
        out.append(
            f"| {kd} | {k} | {pct(sum(x['V', 'raw']['num_ok'] for x in sub) / k)} | "
            f"{pct(sum(x['V', 'raw']['date_ok'] for x in sub) / k)} |"
        )

    v = [x["V", "raw"] for x in rows]
    p1 = sum(a["num_ok"] for a in v) / n
    d1 = sum(a["date_ok"] for a in v) / n
    verdict1 = "GO" if p1 >= 0.95 and d1 >= 0.95 else ("ITERATE" if min(p1, d1) >= 0.80 else "RETHINK")
    out += [
        "",
        f"PREREG §1 (Vision, as scanned, all documents): number {pct(p1)}, date {pct(d1)} → **{verdict1}**.",
        "",
    ]

    sealed = [x for x in rows if "title" in x]
    raw_t = sum(x["title"]["raw"] for x in sealed)
    drop_t = sum(x["title"]["drop"] for x in sealed)
    p1d = sum(x["V", "drop"]["num_ok"] and x["V", "drop"]["date_ok"] for x in rows) / n
    p1r = sum(x["V", "raw"]["num_ok"] and x["V", "raw"]["date_ok"] for x in rows) / n
    if sealed:
        fall = drop_t < raw_t
        verdict2 = (
            "KILL dropout" if fall or p1r - p1d > 0.02 else ("GO for dropout" if p1r - p1d <= 0.01 else "between bars")
        )
        out += [
            "## 2. Red dropout on the seal",
            "",
            f"Last pages with red ink above {pct(RED_PAGE)}: {len(sealed)} of {n}. Seal crop = the largest red blob,",
            "grown to take in the title. Title read = a signer title from a closed list appears in Vision's",
            "read of the crop.",
            "",
            "| Image | Title read |",
            "|---|---:|",
            f"| as scanned | {raw_t} / {len(sealed)} ({pct(raw_t / len(sealed))}) |",
            f"| red dropout | {drop_t} / {len(sealed)} ({pct(drop_t / len(sealed))}) |",
            "",
            f"Page 1 number and date both exact: {pct(p1r)} as scanned, {pct(p1d)} after dropout.",
            f"PREREG §2 → **{verdict2}**.",
            "",
        ]

    out += [
        "## 3. Deterministic checks on Vision's read",
        "",
        "Accepted = a number and a date were read, the date is valid and not in the future, and a year",
        "inside the number equals the date's year. Wrong = number or date differs from the listing.",
        "",
        "| Image | Accepted | Wrong among accepted | 95% upper bound |",
        "|---|---:|---:|---:|",
    ]
    for vv in ("raw", "drop"):
        acc = [x["V", vv] for x in rows if x["V", vv]["pass"]]
        wrong = sum(not (a["num_ok"] and a["date_ok"]) for a in acc)
        if acc:
            out.append(
                f"| {vv} | {len(acc)} / {n} | {wrong} ({pct(wrong / len(acc))}) | {pct(cp_upper(wrong, len(acc)))} |"
            )
    both = [
        x
        for x in rows
        if x["V", "raw"]["pass"]
        and x["V", "raw"]["num"] == x["T", "raw"]["num"]
        and x["V", "raw"]["date"] == x["T", "raw"]["date"]
    ]
    wrong = sum(not (x["V", "raw"]["num_ok"] and x["V", "raw"]["date_ok"]) for x in both)
    if both:
        out.append(
            f"| raw, and Tesseract reads the same | {len(both)} / {n} | {wrong} ({pct(wrong / len(both))}) | {pct(cp_upper(wrong, len(both)))} |"
        )

    out += [
        "",
        "## 4. Post hoc: a stricter parser",
        "",
        "Written **after** seeing the errors of §1–3, so these rows are not part of the pre-registered",
        "test. Most of v1's accepted errors were the parser, not the engine: a date quoted in the title",
        '("Nghị định ... ngày 16 tháng 7 năm 2008") taken when the header date was unreadable, and',
        'dotted leaders ("Số: 10....../2026"). v2 drops dotted leaders, reads the number only right after',
        '"Số" and the date only from the place-date line ("Hà Nội, ngày ...").',
        "",
        "| Engine | Image | Number exact | Date exact | Accepted | Wrong among accepted | 95% upper bound |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for e, en in (("V", "Vision"), ("T", "Tesseract")):
        for vv in ("raw2", "drop2"):
            a = [x[e, vv] for x in rows]
            acc = [y for y in a if y["pass"]]
            wrong = sum(not (y["num_ok"] and y["date_ok"]) for y in acc)
            out.append(
                f"| {en} | {vv[:-1]} | {pct(sum(y['num_ok'] for y in a) / n)} | {pct(sum(y['date_ok'] for y in a) / n)} | "
                f"{len(acc)} / {n} | {wrong} | {pct(cp_upper(wrong, len(acc))) if acc else '—'} |"
            )

    dig = [x for x in rows if not x["scan"]]
    if dig:
        full = [x for x in dig if x["layer"]["num"] and x["layer"]["date"]]
        wrong = sum(not (x["layer"]["num_ok"] and x["layer"]["date_ok"]) for x in full)
        vis = sum(x["V", "raw"]["num_ok"] and x["V", "raw"]["date_ok"] for x in dig)
        out += [
            "",
            "## 5. The text layer does not hold the number or date",
            "",
            f"{len(dig)} documents have a text layer on page 1. The parser of §4 finds both a number and a",
            f"date in it for {len(full)} ({pct(len(full) / len(dig))}), {wrong} of them wrong. In the rest the template",
            'reads "Số:          /2026/TT-BYT Hà Nội, ngày     tháng    năm 2026": the number and the day',
            "and month are added after signing, on top of the page, and are not in the text. On the same",
            f"{len(dig)} documents Vision, reading the rendered page, gets both right for {vis} ({pct(vis / len(dig))}).",
        ]
    return out


if __name__ == "__main__":
    main()
