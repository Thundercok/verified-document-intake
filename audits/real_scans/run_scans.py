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
from analyze import cp_upper, pct  # noqa: E402
from dropout import dropout, red_mask  # noqa: E402

PRIV = Path("data/private/vbcp")
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
    last = np.asarray(Image.open(out / "plast.png").convert("RGB"))
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
    ap.add_argument("--skip-ocr", action="store_true", help="reuse data/private/vbcp/ocr.json")
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

    rows = []
    for r in recs:
        d = PRIV / "pages" / f"{r['id']:03d}"
        truth = listing[r["id"]]
        tn = canon(truth["number"])
        td = tuple(int(x) for x in truth["date"].split("/"))
        row = {"id": r["id"], "kind": tn.split("/")[-1].split("-")[0], "scan": not r["text_layer"], "r": r}
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
        row["layer"] = {"num": r.get("layer_num"), "date": r.get("layer_date")}
        row["layer"]["num_ok"] = row["layer"]["num"] == tn
        row["layer"]["date_ok"] = tuple(row["layer"]["date"] or ()) == td
        if r["seal"]:
            row["title"] = {
                v: has_title(ocr["V"].get(str(d / f"seal{s}.png"), "")) for v, s in (("raw", ""), ("drop", "_drop"))
            }
        rows.append(row)
    (PRIV / "scan_rows.json").write_text(
        json.dumps(
            [{**{k if isinstance(k, str) else "_".join(k): v for k, v in x.items()}} for x in rows],
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    print("\n".join(report(rows)))
    if args.md:
        Path(args.md).write_text("\n".join(report(rows)) + "\n", encoding="utf-8")


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
