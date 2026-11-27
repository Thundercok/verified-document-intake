"""Third reader for the page-1 number (v10): crop the "Số: …" line, read it with Gemma 4 (E4B, ollama).

Vision and Qwen agreed on three wrong handwritten numbers in batches 7 and 9 ("2615" -> 2645,
"2491" -> 249, "02" -> 62). Gemma is a third model family, and it reads a tight crop of the number
line at full scan resolution instead of the 1240 px header Qwen sees.

  crop:  VBCP_DIR=data/private/vbcp9 uv run python audits/real_scans/third_reader.py crop
         (needs boxes.jsonl from vision_boxes.swift; writes pages/NNN/num.png)
  read:  VBCP_DIR=data/private/vbcp9 uv run python audits/real_scans/third_reader.py read
         (ollama serving gemma4:e4b on localhost:11434; appends to gemma_num.jsonl, resumable)
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

from PIL import Image

PRIV = Path(os.environ.get("VBCP_DIR", "data/private/vbcp"))
MODEL = "gemma4:e4b"
PROMPT = (
    "This image shows the number line of a Vietnamese government document, 'Số: <number>/...'. "
    "Some digits may be handwritten. Write the full document number exactly as written "
    "(digits, slashes and letters), and nothing else."
)
SO_RE = re.compile(r"(?:^|\s)(?:S[ốôoóồổ6]|s[ốô])\s*[:.]?\s*(?=\d|$|\s|:)")
NUMISH_RE = re.compile(r"\d+\s*/\s*(?:\d{4}\s*/\s*)?[A-ZĐ]")
LEAD_RE = re.compile(r"\d(?:[\d \-]*\d)?")
# Gemma's spellings of handwritten digits, seen in its reads of batches 1-9 (in-sample): a crossed 7
# as "†", "‡" or "T", an open 4 as "H", a 9 as "g". Folded only before the first "/".
DIGIT_FOLD = str.maketrans({"†": "7", "‡": "7", "T": "7", "H": "4", "g": "9"})


def numline_box(obs: list[dict]) -> tuple[float, float, float, float] | None:
    """The "Số: …" line as (x0, y0, x1, y1) in image fractions, or None.

    The topmost observation that holds "Số" (or, failing that, something shaped like a number);
    the box runs from just left of it to 42% of the width further right and takes in handwriting
    that is taller than the print."""
    hits = [o for o in obs if SO_RE.search(unicodedata.normalize("NFC", o["text"]))]
    if not hits:
        hits = [o for o in obs if NUMISH_RE.search(unicodedata.normalize("NFC", o["text"]))]
    if not hits:
        return None
    o = min(hits, key=lambda o: o["y"])
    h = o["h"]
    return max(0.0, o["x"] - 0.03), max(0.0, o["y"] - 0.8 * h), min(1.0, o["x"] + 0.42), min(1.0, o["y"] + 1.8 * h)


def lead_number(text: str | None) -> int | None:
    """The first run of digits before the first "/", spaces inside it dropped.

    "Số: 2615/QĐ-TTg" -> 2615, "2491QĐ-TTg" -> 2491, "Số:-653/TB-VPC" -> 653, "5 6/2025/TT-BCT" -> 56,
    "14-71 /QĐ-TTg" -> 1471, "3†3/QĐ-TTg" -> 373, "H01/QĐ-TTg" -> 401, "Số:" -> None.
    (Set on the reads of batches 1-9: in-sample.)"""
    t = SO_RE.sub(" ", unicodedata.normalize("NFC", text or "")).split("/")[0].translate(DIGIT_FOLD)
    m = LEAD_RE.search(t)
    return int(re.sub(r"[ \-]", "", m.group(0))) if m else None


def third_ok(number: str, gemma_text: str | None) -> bool:
    """v10: the accepted number's leading digits must equal the leading number Gemma read."""
    g = lead_number(gemma_text)
    head = number.split("/")[0]
    return g is not None and head.isdigit() and int(head) == g


def crop() -> None:
    n = 0
    for line in open(PRIV / "boxes.jsonl", encoding="utf-8"):
        rec = json.loads(line)
        box = numline_box(rec["obs"])
        out = Path(rec["path"]).with_name("num.png")
        if box is None:
            out.unlink(missing_ok=True)
            continue
        im = Image.open(rec["path"]).convert("RGB")
        W, H = im.size
        im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H))).save(out)
        n += 1
    print(f"{n} crops")


def gemma(path: Path) -> str:
    req = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [base64.b64encode(path.read_bytes()).decode()],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 32},
    }
    r = urllib.request.Request(
        "http://localhost:11434/api/generate", json.dumps(req).encode(), {"Content-Type": "application/json"}
    )
    return json.load(urllib.request.urlopen(r, timeout=300))["response"].strip()


def read(paths_file: str | None = None) -> None:
    """Every num.png of the batch, or only those listed in paths_file (one per line)."""
    out_path = PRIV / "gemma_num.jsonl"
    done = set()
    if out_path.exists():
        done = {json.loads(x)["path"] for x in open(out_path, encoding="utf-8") if x.strip()}
    if paths_file:
        wanted = [Path(x.strip()) for x in open(paths_file, encoding="utf-8") if x.strip()]
    else:
        wanted = sorted((PRIV / "pages").glob("*/num.png"))
    todo = [p for p in wanted if str(p) not in done and p.exists()]
    t0 = time.perf_counter()
    with open(out_path, "a", encoding="utf-8") as fh:
        for i, p in enumerate(todo, 1):
            fh.write(json.dumps({"path": str(p), "text": gemma(p)}, ensure_ascii=False) + "\n")
            fh.flush()
            if i % 100 == 0:
                rate = (time.perf_counter() - t0) / i
                print(f"{PRIV.name} {i}/{len(todo)} {rate:.1f}s/crop", flush=True)


if __name__ == "__main__":
    {"crop": crop, "read": read}[sys.argv[1]](*sys.argv[2:])
