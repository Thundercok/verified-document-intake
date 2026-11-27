# VBCP-NumDate: number and date of Vietnamese government documents (tier 1)

3,226 documents from vanban.chinhphu.vn, issued between 24/06/2025 and 24/11/2026, in 8 batches
collected newest-first. Each has two labels: the **document number** ("Số: 2303/QĐ-TTg") and the
**issue date**. Both are what a clerk files a document by. On most scans they are **handwritten
into a typed template** after signing, near a red seal.

This tier holds **metadata only**: source URLs with sha256, labels, page and seal flags, the reads of
three OCR engines on the header, seal and authentication-block crops, and the decisions of the
audited gates v3 to v8. The PDFs (3.5 GB, 53,068 pages) are fetched from the source with
[`download.py`](download.py), which checks every file against its hash. No image is in this
release.

## Read first: what is wrong or missing

- **Labels are the portal listing, not a reading of the page, for 3,215 of 3,226 documents.** The
  listing is not exact:
  - Where a gate's accepted read disagreed with the listing, the page was read blind. 11 listing
    entries turned out wrong. Examples: a wrong PDF attached, a day that differs from the page,
    "QD" for "QĐ", "UBTVVQH15" for "UBTVQH15", "TT-BNNMT" for "TT-BTNMT".
  - These 11 are corrected (`label.source = "adjudicated"`). The other entries were never checked.
  - Some listing numbers contain Cyrillic look-alike letters ("Т", "Р"). 15 entries change under
    `listing_number_normalized`, and `label.number` keeps the raw listing text.
  - The engines' hard cases, which the gates rejected, are exactly the ones never compared with the
    page, so their label error rate is unknown.
- **The same agent built the gates and adjudicated the disagreements.** No independent person read
  any page.
- **The blind spot checks are small.** There are 504 of them, covering batches 4 to 8, about 100
  per batch.
  - They found no wrong number or date, only two Cyrillic "Р" in batch 4.
  - With 0 errors in about 100 checks, up to 3% per batch could still be hidden.
- **Only the header and seal crops were screened for personal data.** The OCR text in this
  release (headers, seals, authentication blocks) was searched for ID-card words, birth dates and
  CCCD-shaped numbers. 12 hits, all signature timestamps or OCR garble, are listed with reasons in
  [`pii_reviewed.json`](pii_reviewed.json).
  - The **body** of the documents was not screened. Some decisions (awards, discipline,
    nationality) can list named individuals on later pages. They are public documents, but this is
    why page images are not released in this tier.
- **Licence of the source documents: not legally verified.** The portal asks that republished
  material credit "Cục Thông tin và Truyền thông Chính phủ" or "www.chinhphu.vn". It links no
  terms-of-use page. Article 15 of the Law on Intellectual Property excludes legal and
  administrative documents from copyright, but this was not checked against the official text for
  this release. Tier 1 redistributes no document, only URLs, hashes and short OCR text of
  headers.
- **The URLs can rot.** Documents can be re-signed or moved. `download.py` reports a changed or
  missing file and does not keep it. In a test on 2026-11-27, 3 of 3 sampled files matched their
  hash.
- **Not representative of commune paperwork.**
  - These are central-government documents: Prime Minister, ministries, National Assembly, the
    Government Office, and a few provinces.
  - They are not civil-status forms, not phone photos, and not CCCD cards.
  - The share of scans grows with age, from 37% in batch 1 to 91% in batch 8.
- **The crops are defined by code, not shipped.**
  - The header is the top 30% of page 1 rendered at 300 dpi. The seal crop is a box around the
    largest red-ink blob of the last page.
  - The exact code is in [`audits/real_scans/run_scans.py`](../audits/real_scans/run_scans.py). It
    renders with macOS PDFKit, so another renderer will give slightly different pixels.

## Files (`vbcp-numdate/`)

| File | Records | What |
|---|---:|---|
| `documents.jsonl` | 3,226 | one document per line (fields below) |
| `ocr.jsonl.gz` | 19,139 | `{doc_id, engine, run, crop, text[, conf_min, conf_mean]}` |
| `croissant.json` | — | Croissant 1.0 metadata, with the sha256 of both files |

`documents.jsonl` fields:
- **Identity and source.**
  - `doc_id` is `vbcp<batch>-<listing index>`.
  - `batch` runs from 1 to 8; `listing_index` is the position within that batch's listing.
  - `url`, `pdf_sha256`, `pdf_bytes` and `pages` describe the PDF.
- **Document type and layout.**
  - `doc_type` is the code taken from the number: QĐ, TT, VBHN, NQ, NĐ, VPCP, TB, CĐ, QH15…
  - `scan` is true when page 1 has no text layer.
  - `text_layer` holds the number and date found in the PDF text layer. It is empty on most signed
    PDFs, because those fields are filled in after signing.
- **Seals and authentication blocks.**
  - `header_red_share` and `last_page_red_share` give the share of red ink on those regions.
  - `seal_on_last_page` is true when red ink covers more than 0.2% of the last page.
  - `auth_block` records whether the v6 or v7 locator found the authentication block of a
    consolidated text (VBHN).
- **Labels.**
  - `listing` holds the number and date as listed. `listing_number_normalized` is the form the
    audits compare: NFC, no spaces, Ð→Đ, Cyrillic→Latin.
  - `label` holds the number, date and `source`: listing or adjudicated.
  - `adjudication` and `spot_check` hold the blind reads from the page, where they exist.
- **Gates.** `gates.v3` … `gates.v8` hold each gate version run on that batch: its output and its
  flags (`ok_listing`, `ok_page`, where it read the number…). A gate that abstained has
  `number: null`.

OCR runs:

| Engine | Crops | Records |
|---|---|---:|
| `apple_vision` | head, head_drop (red-ink dropout), seal, seal_drop, auth, auth7 | 8,842 |
| `tesseract_vie` 5.5 | head, head_drop | 6,452 |
| `qwen3.5-4b` | head_small (every document); full-resolution head for 68 v4 rejections; auth crops | 3,845 |

The Qwen prompt is [`audits/real_scans/header_prompt.txt`](../audits/real_scans/header_prompt.txt).

## Batches

Batches were collected one at a time. Each gate version was frozen and pre-registered before the
batch that tested it ([PREREG.md](../audits/real_scans/PREREG.md)).

| Batch | Docs | Issued | Scans | Seal on last page | Gates run |
|---:|---:|---|---:|---:|---|
| 1 | 193 | 26/10–24/11/2026 | 72 | 141 | v3, v4 |
| 2 | 193 | 30/09–24/10/2026 | 80 | 151 | v3, v4 |
| 3 | 340 | 28/08–30/09/2026 | 159 | 223 | v3, v4 |
| 4 | 500 | 28/06–27/08/2026 | 323 | 272 | v3–v5 |
| 5 | 500 | 22/04–16/06/2026 | 356 | 127 | v3–v5 |
| 6 | 500 | 04/02–31/03/2026 | 373 | 122 | v3–v6 |
| 7 | 500 | 22/10–18/12/2025 | 436 | 84 | v3–v8 |
| 8 | 500 | 24/06–27/07/2025 | 455 | 50 | v3–v8 |

**Suggested use.**
- Batches are disjoint (no URL appears twice) and ordered in time, so splitting by batch measures
  drift, which a random split hides. Tune on batches 1–4 and report on 5–8.
- Batches 5–8 contain more consolidated texts (VBHN) and laws, whose number is not on page 1 or is
  in a harder layout. Report results per `doc_type`.
- For selective prediction, report accepted, wrong, coverage and the binomial upper bound of the
  risk at α = 1%, as [`audits/real_scans/RESULTS_v8.md`](../audits/real_scans/RESULTS_v8.md) does.
- This repository's own gates saw every batch while they were being designed. They are baselines,
  not held-out results.

## Rebuild and download

```bash
uv run python dataset/build.py
```

The build reads `data/private/`, which is not public. It fails if a new identity marker appears in
the OCR text.

```bash
python dataset/download.py --out data/vbcp-numdate-pdf --batch 8
```

The download runs at one request per second, can be resumed, and lists failures in
`failures.tsv`.

## Licence and credit

- The labels, flags, OCR text and metadata in `vbcp-numdate/` are released under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- The code is under the repository's MIT licence.
- The documents themselves are published by the Government of Viet Nam. Credit
  **www.chinhphu.vn (Cục Thông tin và Truyền thông Chính phủ)** when using them, as the portal asks.
