"""Render synthetic dossiers as field-crop images for the real-OCR pilot.

A dossier is one synthetic person plus one invoice. Side A is the anchor (a printed card or
invoice: print fonts, name in capitals, date dd/mm/yyyy, pre-2025 address); side B is a form
filled in by hand (handwriting-style fonts, any date style, either address era). Each field is
one text line on its own image, the unit the OCR engines read.

The crops are plain text lines on a blank background. They do not reproduce the layout, emblem
or security features of any official document, and every value is generated (see
`document_intake.synth`).

Half the dossiers are degraded like a phone photo (slight rotation, blur, uneven lighting,
sensor noise, JPEG). The degradation is drawn per dossier, so both sides of a dossier share it.

Usage: uv run python audits/ocr_pilot/render.py [--n 1000] [--seed 20261124] [--out audits/ocr_pilot/work]
"""

from __future__ import annotations

import argparse
import io
import json
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


def render_dossier(args: tuple[int, int, str]) -> tuple[list[dict], dict]:
    i, seed, out = args
    texts, truth, rng = dossier_texts(i, seed)
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
        if degrade == "photo":
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
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with Pool() as pool:
        results = pool.map(render_dossier, [(i, args.seed, str(out)) for i in range(args.n)], chunksize=8)
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
