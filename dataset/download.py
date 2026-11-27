"""Fetch the PDFs of VBCP-NumDate from their source URLs and check each against its sha256.

Stdlib only. One request per second by default (the rate the batches were collected at). Files
already present with the right hash are skipped, so an interrupted run can be resumed. Each
document lands at <out>/<doc_id>.pdf. A document whose file changed at the source (re-signed,
replaced) or is gone is reported, not kept, and listed in <out>/failures.tsv.

Usage: python dataset/download.py --out data/vbcp-numdate-pdf [--batch 8] [--limit 10] [--delay 1.0]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_INDEX = Path(__file__).resolve().parent / "vbcp-numdate" / "documents.jsonl"
USER_AGENT = "vbcp-numdate-downloader/1.0 (research dataset; 1 request/s)"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def present(path: Path, sha: str) -> bool:
    return path.exists() and digest(path.read_bytes()) == sha


def fetch(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URLs come from the index)
        return resp.read()


def download(docs: list[dict], out: Path, delay: float, get=fetch) -> list[tuple[str, str]]:
    """Returns (doc_id, reason) for every document not saved with the expected hash."""
    out.mkdir(parents=True, exist_ok=True)
    failures = []
    fetched = 0
    for d in docs:
        path = out / f"{d['doc_id']}.pdf"
        if present(path, d["pdf_sha256"]):
            continue
        if fetched and delay:
            time.sleep(delay)
        fetched += 1
        try:
            data = get(d["url"])
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            failures.append((d["doc_id"], f"fetch failed: {e}"))
            continue
        if digest(data) != d["pdf_sha256"]:
            failures.append((d["doc_id"], f"sha256 differs ({len(data)} bytes, expected {d['pdf_bytes']})"))
            continue
        tmp = path.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(path)
    return failures


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--batch", type=int, action="append", help="only these batches (repeatable)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args()

    with open(args.index, encoding="utf-8") as fh:
        docs = [json.loads(line) for line in fh]
    if args.batch:
        docs = [d for d in docs if d["batch"] in args.batch]
    docs = docs[: args.limit]
    failures = download(docs, args.out, args.delay)
    (args.out / "failures.tsv").write_text("".join(f"{i}\t{r}\n" for i, r in failures), encoding="utf-8")
    print(f"{len(docs) - len(failures)} of {len(docs)} present with the expected sha256", file=sys.stderr)
    for i, r in failures[:20]:
        print(f"  {i}: {r}", file=sys.stderr)


if __name__ == "__main__":
    main()
