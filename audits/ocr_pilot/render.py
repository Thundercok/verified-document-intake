"""Render synthetic dossiers as field-crop images for the real-OCR pilot.

A dossier is one synthetic person plus one invoice. Side A is the anchor (a printed card or
invoice: print fonts, name in capitals, date dd/mm/yyyy, pre-2025 address); side B is a form
filled in by hand (handwriting-style fonts, any date style, either address era). Each field is
one text line on its own image, the unit the OCR engines read.

The crops are plain text lines on a blank background. They do not reproduce the layout, emblem
or security features of any official document, and every value is generated (see
`document_intake.synth`).

Suite `photo` (default): half the dossiers are degraded like a phone photo (slight rotation,
blur, uneven lighting, sensor noise, JPEG), grey-scale.

Suite `stress`: the perturbations of docs/RESEARCH_PLAN.md, one condition per dossier in turn,
in colour (a red stamp is only red in colour; Tesseract binarises it to a dark grey):
clean, skew3 / skew7 (+-3 / +-7 degrees), stamp_light / stamp_heavy (a red stamp crossing the
line, translucent or nearly opaque), lowdpi (downsampled to 30-45%), and combined (a stamp, a
3-7 degree skew and low DPI). The stamp is a generic ring reading "MẪU · KHÔNG CÓ GIÁ TRỊ PHÁP
LÝ" with "MẪU" in the centre: it names no authority and carries no emblem.

In both suites the condition is drawn per dossier, so both sides of a dossier share it.

Usage: uv run python audits/ocr_pilot/render.py [--n 1000] [--seed 20261124] [--out audits/ocr_pilot/work]
                                                [--suite photo|stress]
"""

from __future__ import annotations

import argparse
import io
import json
import math
import random
import unicodedata
from dataclasses import asdict, dataclass
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from document_intake.synth import make_amount, make_mst, make_person
from document_intake.synth.render import (
    render_amount_digits,
    render_amount_words,
    render_cccd,
    render_date,
    render_name,
    render_new_address,
    render_old_address,
    render_place,
    render_sex,
)
from document_intake.verify.vn_admin import OLD_TO_NEW

SUP = "/System/Library/Fonts/Supplemental/"
SYS = "/System/Library/Fonts/"
# (file, face index). All checked to render every Vietnamese precomposed letter (no tofu).
PRINT_FONTS = (
    (SUP + "Arial.ttf", 0),
    (SUP + "Arial Bold.ttf", 0),
    (SUP + "Times New Roman.ttf", 0),
    (SUP + "Times New Roman Bold.ttf", 0),
    (SUP + "Courier New.ttf", 0),
    (SUP + "Courier New Bold.ttf", 0),
    (SUP + "Georgia.ttf", 0),
    (SUP + "Tahoma.ttf", 0),
    (SUP + "Verdana.ttf", 0),
)
HAND_FONTS = (
    (SYS + "MarkerFelt.ttc", 0),
    (SYS + "MarkerFelt.ttc", 1),
    (SYS + "Noteworthy.ttc", 0),
    (SYS + "Noteworthy.ttc", 1),
    (SUP + "ChalkboardSE.ttc", 0),
    (SUP + "ChalkboardSE.ttc", 1),
    (SUP + "ChalkboardSE.ttc", 2),
    (SUP + "SignPainter.ttc", 0),
    (SUP + "Savoye LET.ttc", 0),
    (SUP + "SnellRoundhand.ttc", 0),
    (SUP + "Brush Script.ttf", 0),
)

# field -> side. Side A is printed, side B handwritten.
FIELDS = {
    "name_A": "A",
    "dob_A": "A",
    "cccd_A": "A",
    "addr_A": "A",
    "money_digits": "A",
    "mst": "A",
    "name_B": "B",
    "dob_B": "B",
    "cccd_B": "B",
    "addr_B": "B",
    "sex_B": "B",
    "place_B": "B",
    "money_words": "B",
}


@dataclass
class Crop:
    dossier: int
    field: str
    side: str
    text: str  # ground truth, NFC
    path: str
    font: str
    degrade: str


def dossier_texts(i: int, seed: int) -> tuple[dict[str, str], dict[str, object], random.Random]:
    """The rendered text of every field of dossier i, and its underlying values."""
    rng = random.Random(seed * 1_000_003 + i)
    p = make_person(rng)
    amount = make_amount(rng)
    mst = make_mst(rng, branch=rng.random() < 0.3)
    if rng.random() < 0.5:
        addr_b = render_old_address(p.old_address, rng, abbreviate=rng.random() < 0.5)
    else:
        addr_b = render_new_address(p.new_address, rng, abbreviate=rng.random() < 0.5)
    texts = {
        "name_A": render_name(p.name, rng, upper=True),
        "dob_A": render_date(p.dob, rng, "dmy"),
        "cccd_A": p.cccd,
        "addr_A": render_old_address(p.old_address, rng),
        "money_digits": render_amount_digits(amount, rng),
        "mst": mst,
        "name_B": render_name(p.name, rng),
        "dob_B": render_date(p.dob, rng),
        "cccd_B": render_cccd(p.cccd, rng),
        "addr_B": addr_b,
        "sex_B": render_sex(p.sex, rng),
        "place_B": render_place(p.birth_province, OLD_TO_NEW[p.birth_province], rng),
        "money_words": render_amount_words(amount, rng),
    }
    texts = {k: unicodedata.normalize("NFC", v) for k, v in texts.items()}  # print has no Unicode form
    truth = {
        "name": p.name,
        "sex": p.sex,
        "dob": p.dob.isoformat(),
        "birth_province": p.birth_province,
        "cccd": p.cccd,
        "amount": amount,
        "mst": mst,
    }
    return texts, truth, rng


def draw_line(text: str, font_spec: tuple[str, int], size: int, rng: random.Random) -> Image.Image:
    font = ImageFont.truetype(font_spec[0], size, index=font_spec[1])
    left, top, right, bottom = font.getbbox(text)
    pad_x, pad_y = rng.randint(16, 40), rng.randint(12, 28)
    img = Image.new("L", (right - left + 2 * pad_x, bottom - top + 2 * pad_y), 255)
    ink = rng.randint(0, 60)
    ImageDraw.Draw(img).text((pad_x - left, pad_y - top), text, font=font, fill=ink)
    return img


def photo(img: Image.Image, rng: random.Random) -> Image.Image:
    """A phone photo of a page: tilt, defocus, uneven light, sensor noise, JPEG."""
    img = img.rotate(rng.uniform(-2.0, 2.0), resample=Image.BICUBIC, expand=True, fillcolor=255)
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.3)))
    a = np.asarray(img, dtype=np.float32)
    h, w = a.shape
    # Lighting: a linear gradient across the crop and a lowered contrast.
    gx = np.linspace(0, 1, w, dtype=np.float32)[None, :] * rng.uniform(-50, 50)
    gy = np.linspace(0, 1, h, dtype=np.float32)[:, None] * rng.uniform(-30, 30)
    lo, hi = rng.uniform(20, 70), rng.uniform(200, 245)
    a = lo + a / 255.0 * (hi - lo) + gx + gy
    a += np.random.default_rng(rng.randrange(2**32)).normal(0, rng.uniform(3, 10), a.shape)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=rng.randint(35, 75))
    return Image.open(io.BytesIO(buf.getvalue())).convert("L")


STRESS = ("clean", "skew3", "skew7", "stamp_light", "stamp_heavy", "lowdpi", "combined")
STAMP_RED = np.array([196, 32, 44], dtype=np.float32) / 255
STAMP_RING = "MẪU · KHÔNG CÓ GIÁ TRỊ PHÁP LÝ · MẪU · KHÔNG CÓ GIÁ TRỊ PHÁP LÝ · "
STAMP_FONT = PRINT_FONTS[1]  # Arial Bold


def stamp_mask(diam: int, rng: random.Random) -> np.ndarray:
    """Coverage (0-1) of a round stamp: two rings, text around the rim, a word in the centre,
    and uneven ink."""
    m = Image.new("L", (diam, diam), 0)
    d = ImageDraw.Draw(m)
    w = max(2, diam // 45)
    d.ellipse([w, w, diam - w, diam - w], outline=255, width=2 * w)
    r_in = int(diam * 0.31)
    c = diam / 2
    d.ellipse([c - r_in, c - r_in, c + r_in, c + r_in], outline=255, width=w)
    size = max(8, int(diam * 0.075))
    font = ImageFont.truetype(STAMP_FONT[0], size, index=STAMP_FONT[1])
    radius = c - 3 * w - size * 0.6
    start = rng.uniform(0, 360)
    for j, ch in enumerate(STAMP_RING):
        theta = math.radians(start + 360 * j / len(STAMP_RING))
        glyph = Image.new("L", (2 * size, 2 * size), 0)
        ImageDraw.Draw(glyph).text((size, size), ch, font=font, fill=255, anchor="mm")
        glyph = glyph.rotate(-math.degrees(theta), resample=Image.BICUBIC)
        x, y = c + radius * math.sin(theta), c - radius * math.cos(theta)
        m.paste(255, (int(x - size), int(y - size)), glyph)
    big = ImageFont.truetype(STAMP_FONT[0], int(diam * 0.16), index=STAMP_FONT[1])
    d.text((c, c), "MẪU", font=big, fill=255, anchor="mm")
    a = np.asarray(m, dtype=np.float32) / 255
    nrng = np.random.default_rng(rng.randrange(2**32))
    blot = Image.fromarray((nrng.random(a.shape) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(diam / 60))
    b = np.asarray(blot, dtype=np.float32) / 255
    return np.clip(a * (0.35 + 1.3 * (b - b.mean() + 0.5)), 0, 1)


def stamp(img: Image.Image, size: int, heavy: bool, rng: random.Random) -> Image.Image:
    """Multiply a red stamp over the line. A real stamp is many lines tall, so a line crop shows
    one horizontal band of it: rim text and rings, or the centre word."""
    base = np.asarray(img.convert("RGB"), dtype=np.float32) / 255
    h, w, _ = base.shape
    diam = int(size * rng.uniform(5.0, 8.0))
    mask = stamp_mask(diam, rng)
    cx = rng.uniform(0.25, 0.75) * w if heavy else rng.uniform(0, w)
    cy = h / 2 + rng.uniform(-0.25, 0.25) * diam if heavy else h / 2 + rng.uniform(-0.45, 0.45) * diam
    alpha = rng.uniform(0.75, 0.95) if heavy else rng.uniform(0.35, 0.6)
    cov = np.zeros((h, w), dtype=np.float32)
    x0, y0 = int(cx - diam / 2), int(cy - diam / 2)
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(w, x0 + diam), min(h, y0 + diam)
    if xs < xe and ys < ye:
        cov[ys:ye, xs:xe] = mask[ys - y0 : ye - y0, xs - x0 : xe - x0] * alpha
    out = base * (1 - cov[..., None] + cov[..., None] * STAMP_RED)
    return Image.fromarray((out * 255).round().astype(np.uint8))


def skew(img: Image.Image, degrees: float, rng: random.Random) -> Image.Image:
    angle = rng.choice((-1, 1)) * rng.uniform(degrees - 0.5, degrees + 0.5)
    return img.convert("RGB").rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))


def low_dpi(img: Image.Image, rng: random.Random) -> Image.Image:
    f = rng.uniform(0.30, 0.45)
    return img.convert("RGB").resize((max(1, int(img.width * f)), max(1, int(img.height * f))), Image.BOX)


def stress(img: Image.Image, cond: str, size: int, rng: random.Random) -> Image.Image:
    if cond in ("stamp_light", "stamp_heavy"):
        return stamp(img, size, cond == "stamp_heavy", rng)
    if cond in ("skew3", "skew7"):
        return skew(img, 3.0 if cond == "skew3" else 7.0, rng)
    if cond == "lowdpi":
        return low_dpi(img, rng)
    if cond == "combined":
        img = stamp(img, size, rng.random() < 0.5, rng)
        return low_dpi(skew(img, rng.uniform(3.0, 7.0), rng), rng)
    return img.convert("RGB")


def render_dossier(args: tuple[int, int, str, str]) -> tuple[list[dict], dict]:
    i, seed, out, suite = args
    texts, truth, rng = dossier_texts(i, seed)
    if suite == "stress":
        degrade = STRESS[i % len(STRESS)]
    else:
        degrade = "photo" if rng.random() < 0.5 else "clean"
    crops = []
    folder = Path(out) / "img" / f"{i:05d}"
    folder.mkdir(parents=True, exist_ok=True)
    for field, side in FIELDS.items():
        if side == "A":
            font, size = rng.choice(PRINT_FONTS), rng.randint(30, 44)
        else:
            font, size = rng.choice(HAND_FONTS), rng.randint(36, 56)
        img = draw_line(texts[field], font, size, rng)
        if suite == "stress":
            img = stress(img, degrade, size, rng)
        elif degrade == "photo":
            img = photo(img, rng)
        path = folder / f"{field}.png"
        img.save(path)
        name = f"{Path(font[0]).stem}#{font[1]}"
        crops.append(asdict(Crop(i, field, side, texts[field], str(path), name, degrade)))
    return crops, {"dossier": i, "degrade": degrade, **truth}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261124)
    ap.add_argument("--out", default="audits/ocr_pilot/work")
    ap.add_argument("--suite", choices=("photo", "stress"), default="photo")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with Pool() as pool:
        results = pool.map(render_dossier, [(i, args.seed, str(out), args.suite) for i in range(args.n)], chunksize=8)
    with open(out / "crops.jsonl", "w", encoding="utf-8") as fh:
        for crops, _ in results:
            for c in crops:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(out / "dossiers.jsonl", "w", encoding="utf-8") as fh:
        for _, truth in results:
            fh.write(json.dumps(truth, ensure_ascii=False) + "\n")
    print(f"{args.n} dossiers, {sum(len(c) for c, _ in results)} crops -> {out}")


if __name__ == "__main__":
    main()
