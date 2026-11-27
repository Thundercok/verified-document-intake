"""Build the tier-1 release of VBCP-NumDate from the private batches (metadata only, no images).

Reads data/private/vbcp{,2..8}/ and writes dataset/vbcp-numdate/:
- documents.jsonl: one record per document (source URL + sha256, listing and adjudicated labels,
  page/seal flags, and the decisions of the gate versions run on its batch);
- ocr.jsonl.gz: the engine reads of the header, seal and authentication-block crops;
- croissant.json: Croissant 1.0 metadata with the files' sha256.

No PDF or image leaves data/private/. Before writing, every OCR text is screened for identity
markers; a hit fails the build unless dataset/pii_reviewed.json records why it is not personal
data. Usage: uv run python dataset/build.py [--private data/private] [--out dataset/vbcp-numdate]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BATCH_DIRS = {1: "vbcp", **{n: f"vbcp{n}" for n in range(2, 9)}}
CROP_RE = re.compile(r"vbcp(\d*)/pages/(\d+)/(\w+)\.png$")
ENGINES = {"V": "apple_vision", "T": "tesseract_vie"}
# Qwen runs kept in the release (the *_dev runs tuned the prompt on batch 1 and are left out).
QWEN_RUNS = ("qwen", "qwen_full", "qwen_auth", "qwen_auth7", "qwen_all")
# Cyrillic capitals seen in the listing (А В Е К М Н О Р С Т Х), mapped to their Latin look-alikes.
HOMOGLYPHS = str.maketrans("АВЕКМНОРСТХ", "ABEKMHOPCTX")
# Identity markers: an ID-document word, a birth date, or a 12-digit run shaped like a CCCD.
PII_RE = re.compile(
    r"căn cước|\bCCCD\b|\bCMND\b|chứng minh nhân dân|hộ chiếu số|sinh ngày|ngày sinh|\b[0-9]{3}[0-3][0-9]{8}\b",
    re.IGNORECASE,
)
ALLOWED_PII_CONTEXT = re.compile(r"Luật Căn cước|Luật Cơ yếu số|Mã số thông tin quy hoạch", re.IGNORECASE)


def doc_id(batch: int, index: int) -> str:
    return f"vbcp{batch}-{index:04d}"


def iso(d: str | list | tuple | None) -> str | None:
    """dd/mm/yyyy or [d, m, y] -> yyyy-mm-dd (not validated: an engine may read 31/02)."""
    if d is None:
        return None
    day, month, year = (int(x) for x in (d.split("/") if isinstance(d, str) else d))
    return f"{year:04d}-{month:02d}-{day:02d}"


def normalize_number(s: str) -> str:
    """The comparison form used by the audits: NFC, no spaces, Ð as Đ, Cyrillic look-alikes as Latin."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s)).replace("Ð", "Đ").translate(HOMOGLYPHS)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def crop_key(path: str) -> tuple[str, str] | None:
    m = CROP_RE.search(path)
    if not m:
        return None
    return doc_id(int(m.group(1) or 1), int(m.group(2))), m.group(3)


def label(listing: dict, adj: dict | None) -> dict:
    if adj:
        return {"number": adj["number"], "date": iso(adj["date"]), "source": "adjudicated"}
    return {"number": listing["number"], "date": iso(listing["date"]), "source": "listing"}


def gate(v: dict) -> dict:
    out = {k: v[k] for k in v if k not in ("num", "date")}
    return {"number": v.get("num"), "date": iso(v.get("date")), **out}


def load_batch(batch: int, base: Path) -> tuple[list[dict], list[dict]]:
    listing = json.loads((base / "docs.json").read_text(encoding="utf-8"))
    rows = json.loads((base / "scan_rows.json").read_text(encoding="utf-8"))
    read = {n: json.loads((base / f).read_text(encoding="utf-8")) for n, f in
            (("adj", "adjudication.json"), ("spot", "spot_check.json")) if (base / f).exists()}  # fmt: skip
    adjs, spots = read.get("adj", {}), read.get("spot", {})
    docs = []
    for row in rows:
        i, r = row["id"], row["r"]
        pdf = base / "pdf" / f"{i:03d}.pdf"
        entry = listing[i]
        spot = spots.get(str(i))
        docs.append(
            {
                "doc_id": doc_id(batch, i),
                "batch": batch,
                "listing_index": i,
                "url": entry["pdfs"][0],
                "pdf_sha256": sha256(pdf),
                "pdf_bytes": pdf.stat().st_size,
                "pages": r["pages"],
                "doc_type": row["kind"],
                "scan": row["scan"],
                "text_layer": {"number": r.get("layer_num"), "date": iso(r.get("layer_date"))}
                if r["text_layer"]
                else None,
                "header_red_share": round(r["head_red"], 6),
                "last_page_red_share": round(r["last_red"], 6),
                "seal_on_last_page": r["seal"],
                "auth_block": {"v6_locator": bool(r.get("auth")), "v7_locator": bool(r.get("auth7"))},
                "listing": {"number": entry["number"], "date": iso(entry["date"])},
                "listing_number_normalized": normalize_number(entry["number"]),
                "label": label(entry, adjs.get(str(i))),
                "adjudication": adjs.get(str(i)) and {**adjs[str(i)], "date": iso(adjs[str(i)]["date"])},
                "spot_check": spot and {**spot, "date": iso(spot["date"])},
                "gates": {k: gate(row[k]) for k in sorted(row) if re.fullmatch(r"v\d", k)},
            }
        )
    ocr = []
    raw = json.loads((base / "ocr.json").read_text(encoding="utf-8"))
    for code, engine in ENGINES.items():
        for path, text in sorted(raw.get(code, {}).items()):
            if key := crop_key(path):
                ocr.append({"doc_id": key[0], "engine": engine, "run": "pipeline", "crop": key[1], "text": text})
    for run in QWEN_RUNS:
        f = base / f"{run}.jsonl"
        if not f.exists():
            continue
        with open(f, encoding="utf-8") as fh:
            for j in map(json.loads, fh):
                key = crop_key(j["path"])
                if key and not j.get("error") and j.get("text") is not None:
                    ocr.append(
                        {
                            "doc_id": key[0],
                            "engine": "qwen3.5-4b",
                            "run": run,
                            "crop": key[1],
                            "text": j["text"],
                            "conf_min": j.get("conf_min"),
                            "conf_mean": j.get("conf_mean"),
                        }
                    )
    kept = {d["doc_id"] for d in docs}
    return docs, [o for o in ocr if o["doc_id"] in kept]


def pii_hits(ocr: list[dict]) -> list[tuple[str, str, str]]:
    hits = []
    for o in ocr:
        for m in PII_RE.finditer(o["text"]):
            context = o["text"][max(0, m.start() - 40) : m.end() + 40]
            if not ALLOWED_PII_CONTEXT.search(context):
                hits.append((o["doc_id"], o["crop"], re.sub(r"\d{6}(?=\d{6}\b)", "XXXXXX", context)))
    return hits


def jsonl(records: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records).encode()


def gz(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as fh:  # mtime=0: reproducible bytes
        fh.write(data)
    return buf.getvalue()


def croissant(files: dict[str, bytes]) -> dict:
    def field(name: str, dtype: str, desc: str, file: str, path: str | None = None) -> dict:
        return {
            "@type": "cr:Field",
            "@id": f"{file}/{name}",
            "name": name,
            "description": desc,
            "dataType": dtype,
            "source": {"fileObject": {"@id": file}, "extract": {"jsonPath": f"$.{path or name}"}},
        }

    docs = "documents.jsonl"
    ocr = "ocr.jsonl.gz"
    return {
        "@context": {
            "@language": "en",
            "@vocab": "https://schema.org/",
            "cr": "http://mlcommons.org/croissant/",
            "sc": "https://schema.org/",
            "conformsTo": "dct:conformsTo",
            "dct": "http://purl.org/dc/terms/",
        },
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": "VBCP-NumDate",
        "description": (
            "Vietnamese central-government documents from vanban.chinhphu.vn (06/2025-11/2026), in 8 "
            "chronological batches, with the document number and issue date as labels (the portal listing, "
            "corrected by blind adjudication where an accepted read disagreed), page and seal flags, and the "
            "reads of Apple Vision, Tesseract vie and Qwen3.5-4B on header, seal and authentication-block crops. "
            "Tier 1: metadata only; the PDFs are fetched from their source URLs and checked against sha256."
        ),
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "citeAs": "Source documents: www.chinhphu.vn (Cục Thông tin và Truyền thông Chính phủ).",
        "version": "1.0.0",
        "datePublished": "2026-11-27",
        "distribution": [
            {
                "@type": "cr:FileObject",
                "@id": name,
                "name": name,
                "contentUrl": name,
                "encodingFormat": "application/jsonlines",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for name, data in files.items()
        ],
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "documents",
                "name": "documents",
                "key": {"@id": f"{docs}/doc_id"},
                "field": [
                    field("doc_id", "sc:Text", "vbcp<batch>-<listing index>", docs),
                    field("batch", "sc:Integer", "1-8, in the order collected (newest listing first)", docs),
                    field("url", "sc:URL", "first PDF of the document on datafiles.chinhphu.vn", docs),
                    field("pdf_sha256", "sc:Text", "sha256 of the PDF as downloaded", docs),
                    field("doc_type", "sc:Text", "type code from the number (QĐ, TT, NĐ, VBHN...)", docs),
                    field("scan", "sc:Boolean", "page 1 has no text layer", docs),
                    field("label_number", "sc:Text", "document number (label)", docs, "label.number"),
                    field("label_date", "sc:Date", "issue date (label)", docs, "label.date"),
                    field("label_source", "sc:Text", "listing | adjudicated", docs, "label.source"),
                    field("seal_on_last_page", "sc:Boolean", "a red-ink blob above 0.2% of the last page", docs),
                ],
            },
            {
                "@type": "cr:RecordSet",
                "@id": "ocr",
                "name": "ocr",
                "field": [
                    field("doc_id", "sc:Text", "document", ocr),
                    field("engine", "sc:Text", "apple_vision | tesseract_vie | qwen3.5-4b", ocr),
                    field("crop", "sc:Text", "head, head_drop, head_small, seal, seal_drop, auth, auth7...", ocr),
                    field("text", "sc:Text", "the engine's output", ocr),
                ],
            },
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--private", type=Path, default=Path("data/private"))
    ap.add_argument("--out", type=Path, default=ROOT / "vbcp-numdate")
    args = ap.parse_args()

    docs, ocr = [], []
    for batch, name in BATCH_DIRS.items():
        d, o = load_batch(batch, args.private / name)
        docs += d
        ocr += o
        print(f"batch {batch}: {len(d)} documents, {len(o)} OCR records", file=sys.stderr)

    reviewed = json.loads((ROOT / "pii_reviewed.json").read_text(encoding="utf-8"))
    unreviewed = [h for h in pii_hits(ocr) if h[0] not in reviewed]
    if unreviewed:
        for h in unreviewed:
            print("PII screen:", *h, sep=" | ", file=sys.stderr)
        sys.exit(f"{len(unreviewed)} unreviewed identity markers: review them and add to dataset/pii_reviewed.json")

    files = {"documents.jsonl": jsonl(docs), "ocr.jsonl.gz": gz(jsonl(ocr))}
    args.out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (args.out / name).write_bytes(data)
    meta = json.dumps(croissant(files), ensure_ascii=False, indent=2) + "\n"
    (args.out / "croissant.json").write_text(meta, encoding="utf-8")
    print(f"{len(docs)} documents, {len(ocr)} OCR records -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
