# Step 6: real scans with real seals

The stamp results in `../ocr_pilot` used a drawn stamp on single text lines. This step reads
real government documents, with real seals, signatures and the fields a clerk files them by:
the document number and the issue date. Thresholds were written down first: [PREREG.md](PREREG.md).
Numbers: [RESULTS.md](RESULTS.md).

## Data

The first PDF of each of the 250 most recent documents on vanban.chinhphu.vn (listing fetched on
2026-11-25), if at most 5 MB: 193 files, 257 MB, downloaded at one request per second. These are
public documents. The PDFs, page images and OCR text stay under `data/private/vbcp/`
(gitignored); this folder holds code and aggregates only. The listing's number and date are the
ground truth.

## Findings

1. **The number and date are not printed, even on printed documents.** They are filled in when
   the document is issued, after it is signed. On the 72 scans they are written by hand into a
   typed template ("Số: 2303 /QĐ-TTg", "ngày 21 tháng 11"). On the 121 PDFs that have a text
   layer, they are laid over the page; the text layer reads "Số:          /2026/TT-BYT ... ngày
   tháng    năm 2026" for 62% of them. Reading the text layer is safe (0 wrong values where it has
   any) but does not give the two fields. So the narrowed scope still needs OCR of handwritten
   digits, in exactly the fields that index a document.
2. **Vision reads them well, but not well enough for the bar.** Number 94.8%, date 93.8% exact,
   both 89.1% (scans 84.7%, text-layer PDFs 91.7%). The bar set before the run was 95% for each,
   so PREREG §1 gives **ITERATE**. Tesseract `vie` on the same header crops gets both right on 38%.
3. **Red dropout removes real seals cleanly and changes nothing that was scored.** 141 of 193
   last pages carry a seal. Dropout erases them, the mauve seals of the Government Office
   included, leaving a faint ghost. A signer title is read in 113 of 141 seal crops with and
   without dropout, and page-1 accuracy does not move. PREREG §2 gives **GO for dropout**, but the
   test was weak: on these pages the title sits above the seal. The seal covers the signature and
   sometimes the signer's name, which the listing does not give, so that was not scored. Some of
   the 28 misses are the crop cutting the title, not the OCR.
4. **The deterministic checks catch few of the parser's mistakes and none of the engine's.** With
   the pre-registered parser, 179 documents pass the checks and 7 of them are wrong (3.9%, upper
   bound 7.2%). Most of these are the parser: it took a date quoted in the title when the header
   date was unreadable. A stricter parser written after seeing this (RESULTS §4, post hoc) leaves 1
   wrong among 168 accepted (upper bound 2.8%). That one is the engine: a handwritten "2223" read
   as "2023", a valid number with a valid date, which no format check can catch. Only a second
   source would: the issuing office's register, or a second read.
5. **193 documents cannot certify 1%.** A zero-error certificate at α = 1% needs about 230
   accepted units. These numbers are estimates, not guarantees.
6. **The stricter parser did not replicate (confirmation batch, [RESULTS_confirm.md](RESULTS_confirm.md)).**
   v2 was frozen and run on 193 documents not seen before (listing positions 251–500, 30/09 to
   24/10/2026), with bars written first (PREREG.md). It accepts 168 and 4 are wrong: upper bound
   5.4%, above the 5% kill bar, so **KILL v2**. The 1-in-168 of the first batch was optimistic.
   v1 does worse on the same documents (13 wrong of 178, upper bound 11.4%), so the
   pre-registered fallback "back to v1" makes no sense. That was a flaw in how the bar was worded,
   not a reason to move it. The conclusion is that no parser plus format checks meets the bar.
   Of the 4 errors, two are Vision reading the slash as "1" ("7/2026" → "712026"), which hides
   the year from the year check. One is a handwritten "1918" read as "4948". One is an "&" the
   parser does not accept. Vision's exact match also drops on this batch: number 89.1%, date
   92.7%, both 85.5% (ITERATE again). Dropout now costs 1.6 points on page 1, which falls between
   the GO and KILL bars.

**What this means for the plan.** Printed administrative documents are within reach of Apple
Vision, but their key fields carry handwriting or an overlay, and Vision's misreads there are
plausible numbers. The design that holds up is the one the verifier already assumes: compare
against an exact side A (here the issuing register or the publication listing, for a CCCD the QR
code) rather than trust a single read. Red dropout can stay in the pipeline; it costs nothing
measurable.

## Not tested here

- **The signer's name under the seal.** No ground truth.
- **Phone photos.** These are flatbed scans and rendered PDFs.
- **Commune-level documents.** All 193 come from central government; commune paperwork may be
  older, fainter and more often handwritten.
- **The body text.** Only the header and the signer block were read.

## Reproduce

```bash
swiftc -O audits/real_scans/render_pages.swift -o audits/real_scans/work/render_pages
# PDFs in data/private/vbcp/pdf/<listing index>.pdf, listing in data/private/vbcp/docs.json
# Tesseract needs data/tessdata/vie.traineddata (tessdata_best), as for the pilot
uv run python audits/real_scans/run_scans.py --md audits/real_scans/RESULTS.md
# confirmation batch: PDFs in data/private/vbcp2/pdf/, listing in data/private/vbcp2/docs.json
VBCP_DIR=data/private/vbcp2 uv run python audits/real_scans/run_scans.py --confirm --md audits/real_scans/RESULTS_confirm.md
```
