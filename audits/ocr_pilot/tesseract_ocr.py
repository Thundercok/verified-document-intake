"""Batch Tesseract (LSTM, `vie` best model) OCR for the pilot, in parallel.

Each crop is one text line, so page segmentation mode 7 (single line). Output records match
vision_ocr.swift: path, text, conf_min and conf_mean over words (0-1), n_obs (words).

Needs `TESSDATA_PREFIX` pointing at a folder with vie.traineddata (data/tessdata by default).

Usage: uv run python audits/ocr_pilot/tesseract_ocr.py paths.txt out.jsonl [--jobs 8]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
from multiprocessing import Pool


def recognize(path: str) -> dict:
    try:
        proc = subprocess.run(
            ["tesseract", path, "stdout", "-l", "vie", "--psm", "7", "-c", "tessedit_create_tsv=1"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"path": path, "text": "", "conf_min": 0.0, "conf_mean": 0.0, "n_obs": 0, "error": "timeout"}
    words, confs = [], []
    for row in csv.DictReader(io.StringIO(proc.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        conf = float(row.get("conf") or -1)
        if row.get("level") == "5" and text and conf >= 0:
            words.append(text)
            confs.append(conf / 100)
    return {
        "path": path,
        "text": " ".join(words),
        "conf_min": min(confs, default=0.0),
        "conf_mean": sum(confs) / len(confs) if confs else 0.0,
        "n_obs": len(words),
        "error": proc.stderr.strip()[-200:] if proc.returncode else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths")
    ap.add_argument("out")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    args = ap.parse_args()
    os.environ.setdefault("TESSDATA_PREFIX", os.path.abspath("data/tessdata"))
    with open(args.paths, encoding="utf-8") as fh:
        paths = [line.strip() for line in fh if line.strip()]
    with Pool(args.jobs) as pool, open(args.out, "w", encoding="utf-8") as out:
        for rec in pool.imap(recognize, paths, chunksize=16):
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
