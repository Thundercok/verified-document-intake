"""Red-ink dropout: read every crop through its red channel, where a red stamp is nearly white.

Red seal ink reflects red light, so in the red channel it is almost as light as the paper, while
black, grey and blue ink stay dark. This is the "red dropout" that document scanners offer. It
needs no stamp detection and no knowledge of the stamp's exact colour, and it is the identity on
a greyscale image, so gates calibrated on the (greyscale) main batch apply unchanged.

The script also measures how much of each *original* crop is red ink ("red": share of pixels
whose red channel exceeds both others by more than RED_MARGIN). The share is observable before
OCR, so a gate may use it as a stratum (`stress.py`, section 5).

Usage: uv run python audits/ocr_pilot/dropout.py [--work audits/ocr_pilot/work_stress]
       [--out audits/ocr_pilot/work_stress_dropout]
Writes <out>/img/..., <out>/crops.jsonl (new paths, plus "red"), <out>/dossiers.jsonl and
<out>/paths.txt; then run the OCR engines on <out>/paths.txt as for any batch.
"""

from __future__ import annotations

import argparse
import json
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

RED_MARGIN = 40  # of 255: a pixel is red ink if R - max(G, B) exceeds this


def red_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.int16) for i in range(3))
    return r - np.maximum(g, b) > RED_MARGIN


def dropout(src: str, dst: str, whiten: bool = True) -> float:
    """Write the red channel of `src` to `dst`, with pixels that are clearly red ink set to white
    (`whiten`): in the red channel alone a dense stamp still leaves a light grey ghost. Returns the
    share of red-ink pixels."""
    rgb = np.asarray(Image.open(src).convert("RGB"))
    red = red_mask(rgb)
    out = rgb[..., 0].copy()
    if whiten:
        out[red] = 255
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out).save(dst)
    return float(red.mean())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", default="audits/ocr_pilot/work_stress")
    ap.add_argument("--out", default="audits/ocr_pilot/work_stress_dropout")
    args = ap.parse_args()
    work, out = Path(args.work), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with open(work / "crops.jsonl", encoding="utf-8") as fh:
        crops = [json.loads(line) for line in fh]
    dsts = [str(out / Path(c["path"]).relative_to(work)) for c in crops]
    with ProcessPoolExecutor() as ex:
        reds = list(ex.map(dropout, [c["path"] for c in crops], dsts, chunksize=64))

    with open(out / "crops.jsonl", "w", encoding="utf-8") as fh:
        for c, dst, red in zip(crops, dsts, reds, strict=True):
            fh.write(json.dumps({**c, "path": dst, "red": round(red, 5)}, ensure_ascii=False) + "\n")
    (out / "paths.txt").write_text("".join(d + "\n" for d in dsts), encoding="utf-8")
    shutil.copy(work / "dossiers.jsonl", out / "dossiers.jsonl")
    print(f"{len(crops)} crops -> {out}")


if __name__ == "__main__":
    main()
