"""CCCD QR decode test on synthetic payloads (see PREREG.md).

Draws one QR code per made-up person, degrades it under each condition, reads every image with
Apple Vision and compares the decoded string with the generated payload.

Usage: uv run python audits/cccd_qr/run_qr.py [--n 400] [--seed 20261125] [--work audits/cccd_qr/work]
                                             [--md audits/cccd_qr/RESULTS.md]
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import subprocess
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ocr_pilot"))
from render import photo  # noqa: E402

from document_intake.synth import make_person  # noqa: E402

TOOL = Path("audits/cccd_qr/work/qr_tool")
MODULE = 8  # px per module in the drawn code (qr_tool.swift)
CONDITIONS = ("clean", "small", "blur", "skew7", "photo", "glare", "combined")


def payload(rng: random.Random) -> str:
    """One made-up person in the field layout of the CCCD QR code."""
    p = make_person(rng)
    a = p.old_address
    commune = f"{a.commune_kind.capitalize()} {a.commune}"
    district = f"{a.district_kind.capitalize()} {a.district}"
    address = f"{a.street}, {commune}, {district}, {a.province}"
    cmnd = "".join(str(rng.randrange(10)) for _ in range(9))
    issued = date(2021, 1, 1) + timedelta(days=rng.randrange(6 * 365))
    fields = [
        p.cccd,
        cmnd,
        p.name,
        p.dob.strftime("%d%m%Y"),
        "Nam" if p.sex == "nam" else "Nữ",
        address,
        issued.strftime("%d%m%Y"),
    ]
    return unicodedata.normalize("NFC", "|".join(fields))


def to_module(img: Image.Image, px: float) -> Image.Image:
    f = px / MODULE
    return img.resize((max(1, round(img.width * f)), max(1, round(img.height * f))), Image.BOX)


def glare(img: Image.Image, rng: random.Random) -> Image.Image:
    """A bright, soft blob over part of the code, like light on a laminated card."""
    a = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = a.shape
    m = Image.new("L", (w, h), 0)
    r = rng.uniform(0.12, 0.25) * w
    cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.2, 0.8) * h
    ImageDraw.Draw(m).ellipse([cx - r, cy - r * rng.uniform(0.5, 1), cx + r, cy + r * rng.uniform(0.5, 1)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(r / 3))
    k = np.asarray(m, dtype=np.float32) / 255 * rng.uniform(0.6, 0.95)
    return Image.fromarray(np.clip(a * (1 - k) + 255 * k, 0, 255).astype(np.uint8))


def degrade(img: Image.Image, cond: str, rng: random.Random) -> Image.Image:
    if cond == "clean":
        return img
    if cond == "small":
        return to_module(img, rng.uniform(1.5, 2.0))
    if cond == "blur":
        return img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.6) * MODULE))
    if cond == "skew7":
        return img.rotate(rng.choice((-1, 1)) * rng.uniform(6.5, 7.5), Image.BICUBIC, expand=True, fillcolor=255)
    if cond == "photo":
        return photo(to_module(img, rng.uniform(2.5, 4.0)), rng)
    if cond == "glare":
        return glare(img, rng)
    if cond == "combined":
        img = to_module(img, rng.uniform(2.5, 3.5))
        img = img.rotate(rng.uniform(-7, 7), Image.BICUBIC, expand=True, fillcolor=255)
        return photo(glare(img, rng), rng)
    raise ValueError(cond)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--work", default="audits/cccd_qr/work")
    ap.add_argument("--md")
    args = ap.parse_args()
    work = Path(args.work)
    (work / "base").mkdir(parents=True, exist_ok=True)
    (work / "img").mkdir(exist_ok=True)

    rng = random.Random(args.seed)
    truth = {i: payload(rng) for i in range(args.n)}
    jobs = "".join(
        f"{work / 'base' / f'{i:04d}.png'}\t{base64.b64encode(t.encode()).decode()}\n" for i, t in truth.items()
    )
    subprocess.run([str(TOOL), "gen"], input=jobs, text=True, check=True)

    items = []  # (path, id, condition)
    for i in truth:
        base = Image.open(work / "base" / f"{i:04d}.png").convert("L")
        for c in CONDITIONS:
            path = work / "img" / f"{i:04d}_{c}.png"
            degrade(base, c, random.Random(args.seed * 7919 + i * 31 + CONDITIONS.index(c))).save(path)
            items.append((str(path), i, c))
    run = subprocess.run(
        [str(TOOL), "read"], input="".join(p + "\n" for p, _, _ in items), text=True, check=True, capture_output=True
    )
    reads = {r["path"]: r for r in map(json.loads, run.stdout.splitlines())}

    rows = []
    for c in CONDITIONS:
        n = dec = ok = silent = nfc_only = 0
        for path, i, cond in items:
            if cond != c:
                continue
            n += 1
            ps = reads[path]["payloads"]
            if not ps:
                continue
            dec += 1
            got = ps[0]
            if got == truth[i]:
                ok += 1
            else:
                silent += 1
                nfc_only += unicodedata.normalize("NFC", got) == truth[i]
        rows.append((c, n, dec, ok, silent, nfc_only))

    out = [
        "# CCCD QR decode: synthetic payloads",
        "",
        f"Generated by `audits/cccd_qr/run_qr.py` (n = {args.n} made-up people, seed {args.seed}, error",
        "correction M). Read by Apple Vision `VNDetectBarcodesRequest`. Thresholds: PREREG.md.",
        "Upper bound: a clean generated code degraded in software, not a photographed card.",
        "",
        "| Condition | Codes | Decoded | Exact | Silent errors | of which NFC/NFD only |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for c, n, dec, ok, silent, nfc_only in rows:
        out.append(f"| {c} | {n} | {dec / n:.1%} | {ok} | {silent} | {nfc_only} |")
    total_dec = sum(r[2] for r in rows)
    total_silent = sum(r[4] for r in rows)
    out += [
        "",
        f"Silent errors in all: {total_silent} of {total_dec} decodes. Verdict by PREREG.md §1: "
        + ("**GO**" if total_silent == 0 else "**KILL**")
        + ".",
    ]
    text = "\n".join(out) + "\n"
    if args.md:
        Path(args.md).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
