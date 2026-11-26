# Pre-registration: real scans with real seals

Written on 2026-11-25, after looking at one sample page and before any OCR of the set.

## Data

The first PDF of each of the 250 most recent documents listed on vanban.chinhphu.vn, if it is
at most 5 MB: 193 files. Public government documents. The listing gives each document's number
("2303/QĐ-TTg") and issue date; these are the ground truth. Nothing else is labelled.

Seen on the sample before writing this: the number and the day and month are filled in **by
hand** on a typed template, and the red seal sits on the signer block, not on the number or date.

## Fields and engines

- Page 1: the document number after "Số" and the issue date ("ngày .. tháng .. năm ..").
- Last page: the signer block under the seal (title such as "THỦ TƯỚNG", "KT. BỘ TRƯỞNG").
- Engines: Apple Vision and Tesseract `vie`, on the page as scanned and after red-ink dropout
  (R − max(G, B) > 40 set to white, the rule of `audits/ocr_pilot/dropout.py`).

## Thresholds (fixed now, not to be moved after the results)

1. **Printed scope.** Vision's exact-match rate on page 1, as scanned:
   GO if number ≥ 95% and date ≥ 95%; ITERATE if both ≥ 80%; RETHINK below 80% (then the number
   and date of real documents have to come from somewhere other than OCR).
2. **Red dropout on real seals.** On last pages that carry red ink (share > 0.2%), the share
   where a signer title from a closed list is read:
   GO for dropout if it does not fall and page-1 exact match drops by at most 1 point;
   KILL dropout if the title share falls or page-1 exact match drops by more than 2 points.
3. **Verifier.** Among Vision reads that pass the deterministic checks (well-formed number, a
   year inside the number equal to the year of the date, a valid date not after the listing
   date), the share that is still wrong, with its 95% upper bound. No GO bar: 193 documents
   cannot certify 1% (a zero-error certificate needs about 230 units).

## Confirmation batch (written 2026-11-26, before listing or downloading it)

The parser of RESULTS §4 ("v2": `read_number2`, `read_date2`, `checks_pass`) was written after
seeing the errors of the first 193 documents, so its 1-in-168 is optimistic. It is frozen as of
commit a0bdc77 and run unchanged on documents the project has not seen: listing positions 251–500
on vanban.chinhphu.vn as of 2026-11-26, minus any already in the first batch, first PDF at most
5 MB. Only input paths may change in the code; no parser or check.

1. **Primary.** Vision, as scanned, v2: wrong among accepted, with its 95% upper bound.
   GO (v2 becomes the parser) if the upper bound is ≤ 3%; KILL v2 (back to v1, and the §4 gain is
   reported as not replicated) if it is > 5%; ITERATE in between.
2. **Replication of §1.** Vision number and date exact match, same bars as §1 (≥ 95% each).
3. **Certificate.** Computed on this batch alone, never pooled with the first 193 (v2 was fitted
   to them). A zero-error certificate at α = 1%, δ = 0.1 needs at least 230 accepted documents;
   if fewer are accepted, say so and do not certify.

## Third batch (v3) (written 2026-11-26, before listing or downloading it)

The confirmation batch killed v2. v3 was then written on batches 1 and 2 (386 documents), so its
numbers there are in-sample:

- `read_number3` (v2 plus "&"), `read_date2`, and `checks_pass3`: `checks_pass` plus "TT, NĐ,
  VBHN, TTLT and QH numbers carry a /YYYY/ segment" (true for 496 of the 498 listed numbers of
  batches 1 and 2, the two exceptions being VBHN). This catches the slash read as "1".
- A second read: Qwen3.5-4B (MLX 4-bit, greedy, 96 tokens) on the header crop scaled to 1240 px
  wide, with `header_prompt.txt`. A document is accepted only if Qwen's number and date equal
  Vision's.

On batches 1 and 2 the rules alone accept 334, 2 wrong (both handwritten digits: "2223" read as
"2023", "1918" as "4948"). Adding the agreement accepts 296 (76.7%), 0 wrong. Qwen disagrees on
both errors, and also rejects 36 documents that Vision read correctly. Qwen is not independent of
Vision: at full resolution it made the same "2223" → "2023" error.

v3 is frozen as of the commit that adds this section: `run_scans.py`, `header_prompt.txt`,
`vlm_ocr.py`, the model and the 1240 px scale. Only input paths may change.

**Data.** Listing positions 501 onward on vanban.chinhphu.vn as listed on 2026-11-26, skipping
any document already in batch 1 or 2, first PDF at most 5 MB, in listing order, until 340 PDFs
are downloaded. 340 is set so that about 260 are expected to be accepted at the dev coverage (76.7%), and about
250 at the lower batch-1 coverage (73.6%), both above the 230 the certificate needs.

1. **Primary.** v3 (rules + agreement): wrong among accepted, with its 95% upper bound.
   GO if the upper bound is ≤ 3%; KILL v3 if it is > 5% (then two on-device engines that agree
   are not a second source, and the number and date need an exact side A such as the issuing
   register); ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%. Below that, v3 sends too much to a person to be worth its
   cost, whatever its error rate.
3. **Certificate.** On this batch alone, never pooled with batches 1 and 2. At α = 1%, δ = 0.1 it
   needs at least 230 accepted and, in practice, no error (one error needs 388 accepted). If the
   batch falls short, say so and do not certify. A certificate covers central-government
   documents on this site in this period, not commune paperwork.
4. **Report only.** The rules alone, and how many correct Vision reads Qwen's disagreement costs.
