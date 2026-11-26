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

## Fourth batch (v4) (written 2026-11-26, before listing or downloading it)

v3 passed its bar on the third batch (upper bound 2.9%), and its three errors against the listing
were listing faults. v4 was then written on all 726 documents of batches 1–3, so its numbers there
are in-sample: 574 accepted (79.1%), 0 wrong against the page, 3 listing faults (batch 3 alone:
247 of 340, 72.6%).

v4 (`read_v4`, stage 1 only): every number Vision's header text could stand for
(`read_numbers4`), Vision's date (`read_date2`), `checks_pass3`, the e-signature check
(`emblem_ok`: if the page prints an e-signature time, the issue date must be 0–14 days before
it), and agreement with Qwen3.5-4B's read of the 1240 px header (`agree4`: "Đ"/"D" and a
day-month swap tolerated in Qwen's read). Accepted only if exactly one candidate passes and
agrees. It is frozen as of the commit that adds this section; only input paths may change.

**Data.** Listing positions 1001 onward on vanban.chinhphu.vn as listed on 2026-11-26, skipping
any document already in batches 1–3, first PDF at most 5 MB, in listing order, until 500 PDFs
are downloaded. At the dev coverage (72.6–85.5% per batch) that is 360–430 accepted: enough for a
certificate with no error, and with one error if coverage is at least 78%.

**Truth: the page, adjudicated blind.** The listing is wrong about 1% of the time, so truth is
the listing except where it disagrees with an accepted read. For each such document
(`run_scans.py --to-adjudicate` prints the ids only), a reader opens the header image without
seeing any engine's read or the listing's value, writes the number and date the page shows into
`adjudication.json`, and that becomes the truth. If the page cannot be read with certainty, the
listing stands. Documents that agree with the listing are not looked at; a listing fault that
both engines reproduce exactly would be missed, which is reported as a limit.

1. **Primary.** v4, wrong against the page among accepted, 95% upper bound. GO if ≤ 3%;
   KILL v4 if > 5%; ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%.
3. **Certificate.** On this batch alone, never pooled with batches 1–3. Binomial test at
   α = 1%, δ = 0.1 (`binom_cdf(k, n, α) ≤ δ`, n ≥ 230). If it passes, the claim is: on central
   government documents published on this site in this period, v4's accepted number-and-date
   pairs are wrong at most 1% of the time, with 90% confidence. Not commune paperwork, not phone
   photos.
4. **Report only.** Errors against the listing as published; the full-resolution Qwen re-read of
   rejections (it let a shared error through on dev); scans versus PDFs.

## Blind spot check of the fourth batch (written 2026-11-26, after scoring batch 4, before drawing the sample)

The batch-4 truth was the listing, except for the 2 accepted documents that disagreed with it. An
accepted document whose listing entry is wrong in exactly the way both engines read it would not
have been looked at. This check measures that blind spot. It cannot confirm the certificate: 0 of
100 still allows a hidden-error rate of up to 3.0% (one-sided 95%). What it can do is falsify the
certificate. One hidden error makes the count 2 of 395, and 2 errors need at least 531 accepted
documents.

**Population.** The 394 batch-4 documents that v4 accepts at stage 1 and that agree with the
listing (233 scans).

**Sample.** 100 ids drawn by `random.Random(20261126).sample(sorted(ids), 100)`, drawn after
this section is committed. The script prints the ids only.

**Reading.** For each id, the reader sees only that page's header image. The image is cropped
to a band from 30% to 65% of the header's height and is otherwise as rendered. If the number line
or the date line falls outside the band, the reader is shown the full header. The reader sees no
engine read and no listing value, and writes the number and date the page shows into
`data/private/vbcp4/spot_check.json`, or "?" for a field that cannot be read with certainty. This
is the same reader as the adjudication: the agent that built v4. That is a limit.

**Scoring.** The reader's reads are compared with the value both the listing and v4 give. The
comparison folds "Đ"/"D", ignores spacing and maps Cyrillic letters to Latin. If they differ, the
reader looks at that field again, zoomed in, knowing only that there is a mismatch and not the
value. The reader then keeps or corrects their read. A confirmed mismatch, where the reader is sure,
is a hidden error. A mismatch the reader withdraws is a reader error. Both counts are reported.

1. **Primary.** If there is at least 1 hidden error, the batch-4 certificate is withdrawn and the
   README says so. If there are 0, the certificate stands and the README reports the 3.0% bound
   that this check leaves.
2. **Report only.** The number of "?" fields, the reader-error count, and scans versus PDFs.
