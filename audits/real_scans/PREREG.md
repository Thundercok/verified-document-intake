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

## Fifth batch (v5) (written 2026-11-26, before listing or downloading it)

v4 passed on batch 4 (1 wrong in 395 accepted, upper bound 1.2%, certificate p = 0.094). Its one
error was "QĐ" written as "QD": Vision dropped the stroke, the Đ/D tolerance let it agree with
Qwen, and v4 output Vision's spelling. v5 (`read_v5`) is `read_v4` plus `merge_d`. If Vision's
read and the agreeing Qwen read differ only in "Đ"/"D", then segment by segment Qwen's spelling
replaces Vision's only when Vision's segment is not a code in `issuer_codes.txt` and Qwen's is.
That file holds the 69 letter segments in the listings of batches 1–4. The rule is narrower than
"keep Đ if either engine saw it", which was tried first: Qwen also adds the stroke ("BGDĐT" read
as "BGĐĐT"), and that version broke 3 documents in-sample. In-sample on batches 1–4 (1,226
documents), v5 differs from v4 on 1 document, the batch-4 error, and accepts 969 with 0 wrong
against the page. v5 is frozen as of the commit that adds this section: `run_scans.py`,
`issuer_codes.txt`, `header_prompt.txt`, `vlm_ocr.py`, the model and the 1240 px scale. Only input
paths may change.

**Data.** Pages 37 onward of the listing on vanban.chinhphu.vn as of 2026-11-26, read with the
batch-4 lister (50 documents a page, older than batch 4). Any document whose number is in the
listings of batches 1–4 is skipped. First PDF at most 5 MB, in listing order, until 500 PDFs are
downloaded.

**Truth: the page, read blind, with no person involved.** All reads are by the agent that built
v5. It sees a header image and nothing else: no engine read and no listing value. This is the
same limit as batch 4.
- Every v5 accept that disagrees with the listing (`--to-adjudicate5`, ids only) is read from the
  full header and written to `adjudication.json`. If the page cannot be read with certainty, the
  listing stands.
- A spot check of the accepts that agree with the listing: 100 ids drawn by `--spot5`
  (`random.Random(20261127).sample`), each read from the 30–65% band of the header, or the full
  header if a field falls outside the band, into `spot_check.json`. If a read disagrees with the
  listing, the reader looks again, zoomed in, knowing only that there is a mismatch. A read the
  reader confirms goes into `adjudication.json` and counts as an error in the primary. A read the
  reader withdraws is reported as a reader error.
- Hidden errors among the roughly 290 agreeing documents that are not sampled stay unseen. This
  is reported as a limit.

1. **Primary.** v5, wrong against the page among accepted, with its 95% upper bound. GO if ≤ 3%;
   KILL v5 if > 5%; ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%.
3. **Certificate.** On this batch alone, never pooled. Binomial test at α = 1%, δ = 0.1
   (n ≥ 230). The claim if it passes is the same as for batch 4: central government documents
   on this site, this period, accepted pairs wrong at most 1% of the time with 90% confidence. If
   the spot check finds a hidden error, it counts. If it finds none, the README restates that up
   to about 3% of the unsampled agreeing documents could still hide one.
4. **Report only.** v4 on the same documents; scans versus PDFs; errors against the listing as
   published; "?" fields and reader errors in the spot check. No full-resolution re-read this time.

## Sixth batch (v6) (written 2026-11-27, before listing or downloading it)

v5 passed risk on batch 5 (0 wrong in 328 accepted, upper bound 0.9%, certificate p = 0.037) but
missed coverage (65.6% against 70%). The misses were mostly consolidated texts (VBHN): 81 of the
500, and v5 accepted none. Two causes, both seen in batch 5 and therefore in-sample:
1. In 2026 VBHN numbers dropped the year ("37/VBHN-BXD"; no year in 0 of 42 listed VBHN in batch
   1, 48 of 86 in batch 4, 127 of 127 in batch 5). v3–v5 demanded a year for VBHN.
2. A VBHN page 1 has no "Số:" line. The number and date are printed in the authentication block
   ("XÁC THỰC VĂN BẢN HỢP NHẤT") at the end of the main text, laid out like a header.

v6 (`read_v6`) is v5 with two changes:
- `checks_pass6`: a VBHN number may have no year segment if its leading number has at most 4
  digits (so "712026/VBHN", a slash read as "1", still fails). Nothing else changes.
- If page 1 gives no accept, the authentication block is looked for in the PDF text layer
  (`auth_locate`: the last page holding the phrase, and its height). That page is rendered and a
  full-width band from 3% above to 8% below the phrase is cropped (`auth.png`, and `auth_small.png`
  at 1240 px for Qwen). Vision and Qwen read it with the same prompt as the header, and the same
  `accept` rule applies (date, emblem, format checks, exactly one candidate agreeing with Qwen,
  `merge_d`), except that only a VBHN number is accepted from it. Scans have no text layer, so v6
  never finds the block in a scan and abstains on a scanned VBHN with no number on page 1.

In-sample (batches 1–5, 1,726 documents, all reads already made; truth = listing except
`adjudication.json`): v6 accepts 1,362 (v5: 1,297), 0 wrong; every
v5 accept is kept. By batch: 162, 165, 248, 408 and 379 of 193, 193, 340, 500 and 500 (v5: 162, 165,
247, 395, 328). From the block: 6 in batch 4 and 51 in batch 5 (of 24 and 62 blocks found). All 553
VBHN numbers in the five listings pass checks_pass6. The 57 block accepts were not read blind, so
"0 wrong" for them is against the listing only. In batch 5 these numbers lift coverage from 65.6%
to 75.8%, but on the data v6 was built on. v6 is frozen as of the commit that adds this section:
`run_scans.py`, `issuer_codes.txt` (unchanged from v5), `header_prompt.txt`, `vlm_ocr.py`, the
model and the 1240 px scale. Only input paths may change.

**Data.** Pages 57 onward of the listing on vanban.chinhphu.vn as of 2026-11-27, read with the
batch-5 lister (older than batch 5). Any document whose number is in the listings of batches 1–5
is skipped. First PDF at most 5 MB, in listing order, until 500 PDFs are downloaded. These
documents are older, so fewer VBHN may lack the year; that is part of what is tested.

**Truth: the page, read blind, with no person involved.** As batch 5. All reads are by the agent
that built v6; it sees an image and nothing else: no engine read, no listing value.
- Every v6 accept that disagrees with the listing (`--to-adjudicate6`, ids only) is read from the
  image the accept came from (the full header, or `auth.png` for an accept from the block) and
  written to `adjudication.json`. If the image cannot be read with certainty, the listing stands.
- A spot check of the accepts that agree with the listing: 100 ids drawn by `--spot6`
  (`random.Random(20261128).sample`), each read from the 30–65% band of the header, or from
  `auth.png` for an accept from the block, into `spot_check.json`. A mismatch is looked at again,
  zoomed in, knowing only that there is a mismatch. A confirmed read goes into `adjudication.json`
  and counts as an error; a withdrawn read is reported as a reader error. Hidden errors among the
  unsampled agreeing accepts stay unseen; this is reported as a limit.

1. **Primary.** v6, wrong against the page among accepted, with its 95% upper bound. GO if ≤ 3%;
   KILL v6 if > 5%; ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%.
3. **Certificate.** On this batch alone, never pooled. Binomial test at α = 1%, δ = 0.1
   (n ≥ 230). Same claim as for batches 4 and 5 if it passes.
4. **Report only.** v5 on the same documents; scans versus PDFs; VBHN versus the rest (by the
   listing's type); accepts from the authentication block, with their errors; errors against the
   listing as published; "?" fields and reader errors in the spot check.

## Seventh batch (v7) (written 2026-11-27, before listing or downloading it)

v6 passed both bars on batch 6 (0 wrong in 355 accepted, upper bound 0.8%, certificate p = 0.028;
coverage 71.0%, one point over the bar, 95% interval 66.9–74.8%). VBHN stayed the weak part: 31 of
107 accepted, all from the authentication block. Looked at after scoring, so in-sample: of the 98
VBHN with a text layer, `auth_locate` missed the block in 59. Two causes: the National Assembly
Office (VPQH) text layer is an OCR layer with a broken font ("xAc THl/C VAN BAN HQP NHA T"), so
`AUTH_RE` never matches; and in clean layers the phrase is split over text fragments in ways the
8-fragment window misses.

v7 (`auth_locate7`) changes only the locator. Each text fragment is folded (marks stripped, upper
case, A–Z and 0–9 only), the fragments are joined with an index map, and the pattern
`XACTH\w{0,3}VANBANH\w{0,3}PN(H|II|B)AT` is searched; the block is placed at the fragment where the
last match on the page starts. The page is the last page with a match. Crop, prompt, reading and
the accept rule are v6's (`read_v6`, VBHN numbers only from the block). Scans still have no path.

In-sample (batches 1–6, 2,226 documents, reads already made; truth = listing except
`adjudication.json`; the new accepts in batches 1–6 were not read blind): IN_SAMPLE.
- The v7 locator finds every block v6 found, on the same page, with a pixel-identical crop (125 of
  125 in batches 4–6), and 119 more, all in VBHN; it finds none in a document that is not a VBHN.
- Accepted, v6 → v7: batch 1 162 → 162, batch 2 165 → 165, batch 3 248 → 248, batch 4 408 → 409,
  batch 5 379 → 384, batch 6 355 → 396 (79.2%; VBHN 31 → 72 of 107). 0 wrong in all six. v7 cannot
  lose a v6 accept: page 1 is unchanged and every v6 block is a v7 block with the same crop.
- From batch 7 on, v6 (report only) reuses the v7 reads of a block v6 also finds (same image).

v7 is frozen as of the commit that adds this section: `run_scans.py`, `issuer_codes.txt`
(unchanged from v5), `header_prompt.txt`, `vlm_ocr.py`, the model and the 1240 px scale. Only
input paths may change.

**Data.** Pages 81 onward of the listing on vanban.chinhphu.vn as of 2026-11-27, read with the
batch-6 lister (older than batch 6). Any document whose number is in the listings of batches 1–6
(downloaded or not) is skipped. First PDF at most 5 MB, in listing order, until 500 PDFs are
downloaded. These documents are older again; how many VBHN they hold is part of what is tested.

**Truth: the page, read blind, with no person involved.** As batch 6, except the spot check. All
reads are by the agent that built v7; it sees an image and nothing else: no engine read, no
listing value.
- Every v7 accept that disagrees with the listing (`--to-adjudicate7`, ids only) is read from the
  image the accept came from (the full header, or `auth7.png`) and written to `adjudication.json`.
  If the image cannot be read with certainty, the listing stands.
- Spot check of the accepts that agree with the listing (`--spot7`): **every** accept from the
  authentication block, read from `auth7.png`, because the block is the path v7 widens; and 100
  accepts from page 1 drawn by `random.Random(20261129).sample`, read from the 30–65% band of the
  header. Into `spot_check.json`. A mismatch is looked at again, zoomed in, knowing only that there
  is a mismatch. A confirmed read goes into `adjudication.json` and counts as an error; a withdrawn
  read is reported as a reader error. Hidden errors among the unsampled page-1 accepts stay unseen;
  this is reported as a limit.

1. **Primary.** v7, wrong against the page among accepted, with its 95% upper bound. GO if ≤ 3%;
   KILL v7 if > 5%; ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%.
3. **Certificate.** On this batch alone, never pooled. Binomial test at α = 1%, δ = 0.1
   (n ≥ 230).
4. **Report only.** v6 and v5 on the same documents; scans versus PDFs; VBHN versus the rest (by
   the listing's type); accepts from the block, with their errors; errors against the listing as
   published; "?" fields and reader errors in the spot check.

## Eighth batch (v8) (written 2026-11-27, before listing or downloading it)

v7 on batch 7: 350 of 500 accepted (70.0%, exactly at the bar), 2 wrong against the page, upper
bound 1.8%, certificate p = 0.319, not certified. Both errors were handwritten numbers on page 1
that Vision and Qwen read the same wrong way. Looked at after scoring, so in-sample:
- id 366: Vision read "2491QĐ-TTg" with no slash. `read_numbers4` turns that into two candidates
  that both pass the checks, 2491 and 249 (slash read as "1"). Qwen said 249; v7 took it.
- id 192: "2615/QĐ-TTg", read 2645 by both. On the same day the same register issued 2622 and
  2623; 2634 is dated three days later. The number does not fit the register's order.

v8 (`read_v8`, `register_drop`) is v7 with two abstentions:
- **A.** If more than one candidate passes the checks, abstain (on page 1 and in the block). Qwen
  sees the same pixels Vision found unclear, so it is not an independent tie-breaker.
- **B.** Within the batch, accepts are grouped by register (the part after the number, the number
  of "/" segments, the year of the date). Two accepts conflict when the higher number carries the
  earlier date. The accepts in the most conflicts are dropped, all of them on a tie, until none
  conflict. B uses only the batch's own reads, never the listing. With few documents from one
  register it does nothing; on a single document it does nothing.

In-sample (batches 1–7, 2,726 documents, reads already made; truth = listing except
`adjudication.json`; B's rule shape and the register key were chosen after seeing the two errors,
so this is tuned on n = 2): IN_SAMPLE.
- v7 → v8 accepted: batch 1 162 → 161, batch 2 165 → 162, batch 3 248 → 248, batch 4 409 → 404,
  batch 5 384 → 378, batch 6 396 → 394, batch 7 350 → 347. In all: 2,114 → 2,094; both errors
  dropped, 18 correct accepts lost (A: 4 correct and id 366; B: 14 correct and id 192). 0 wrong left.
- Keying registers without the "/" count (so "48/2025/QĐ-TTg" and "2336/QĐ-TTg" share one) put
  614 listing truths in conflicting pairs; with it, 53. Real registers are not strictly in order.
- **Coverage risk, stated before the run:** v8 on batch 7 is 69.4%, under the bar. v8 trades about
  one point of coverage for the two errors. If batch 8 is like batch 7, coverage can miss.

v8 is frozen as of the commit that adds this section: `run_scans.py`, `issuer_codes.txt`
(unchanged), `header_prompt.txt`, `vlm_ocr.py`, the model and the 1240 px scale. Only input paths
may change.

**Data.** Pages 111 onward of the listing on vanban.chinhphu.vn as of 2026-11-27, read with the
batch-7 lister (older than batch 7). Any document whose number is in the listings of batches 1–7
(downloaded or not) is skipped. First PDF at most 5 MB, in listing order, until 500 PDFs are
downloaded.

**Truth: the page, read blind, with no person involved.** As batch 7. All reads are by the agent
that built v8; it sees an image and nothing else: no engine read, no listing value.
- Every **v7** accept that disagrees with the listing (`--to-adjudicate7`; v8's accepts are a
  subset of v7's) is read from the image the accept came from (the full header, or `auth7.png`) and
  written to `adjudication.json`. If the image cannot be read with certainty, the listing stands.
- Spot check (`--spot8`): every v8 accept from the block that agrees with the listing, read from
  `auth7.png`, and 100 v8 accepts from page 1 that agree with it, drawn by
  `random.Random(20261130).sample`, read from the 30–65% band of the header. Into
  `spot_check.json`. A mismatch is looked at again, zoomed in, knowing only that there is a mismatch.
  A confirmed read goes into `adjudication.json` and counts as an error; a withdrawn read is
  reported as a reader error. Hidden errors among the unsampled accepts stay unseen.

1. **Primary.** v8, wrong against the page among accepted, with its 95% upper bound. GO if ≤ 3%;
   KILL v8 if > 5%; ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%.
3. **Certificate.** On this batch alone, never pooled. Binomial test at α = 1%, δ = 0.1
   (n ≥ 230).
4. **Report only.** v7 on the same documents; v7 accepts dropped by A and by B, with how many were
   wrong against the page; scans versus PDFs; VBHN versus the rest; accepts from the block, with
   their errors; errors against the listing as published; reader errors in the spot check.

## Ninth batch (v9) (written 2026-11-27, before listing or downloading it)

v8 on batch 8: 313 of 500 accepted (62.6%, bar 70% missed), 0 wrong against the page, upper bound
1.0%, certificate p = 0.043, certified. Looked at after scoring, so in-sample: v8's rejections on
page 1 over batches 1–8 (3,226 documents) are mostly documents with no date on page 1 (486), and
among National Assembly documents all 111 laws and resolutions "…/QH15" have none: their date is in
the closing sentence "… thông qua ngày 25 tháng 6 năm 2025" on the last page. Of the 160
"NQ-UBTVQH" resolutions, 46 were lost because Vision and Qwen spelled the issuer part differently
("NQ-UBTVQH1S", "NO-UBTVQHIS" from Vision); finding 14 put this on the issuer-code check, which was
wrong: the two engines disagreed (`agree4`). Rule B dropped 5 correct accepts in batch 8 because
"48/2025/QĐ-UBND" and "53/2025/QĐ-UBND" from different provinces shared one register key.

v9 (`read_v9`, `accept9`, `merge9`, `register_drop9`) is v8 with three changes:
- **L.** If page 1 gives no date, Vision's read of the last page (`plast.png`) gives it: the last
  "thông qua ngày … tháng … năm …" sentence. Qwen reads `plast_small.png` (1240 px) with
  `passed_prompt.txt`, and must give the same date (day and month may be swapped, as `agree4`). The
  number comes from page 1 as before: exactly one candidate passing `checks_pass6` with that date
  (so its year must be the date's year), agreeing with Qwen's header read. The e-signature emblem on
  page 1 is checked with 0–45 days (`EMBLEM_DAYS_L`) instead of 0–14: on the 146 QH/UBTVQH
  documents of batches 1–8 that print an emblem, the listing date to the emblem is 0–45 days but
  for one (244). This window was set on batches 1–8.
- **T.** Vision's candidate and Qwen's number are compared on the part after the last "/" under
  OCR look-alikes (O Q → 0, I l | → 1, S → 5, Đ → D); everything before the last "/" must be
  identical. Where the two differ in a "-" segment, the segment is taken from the engine whose
  spelling is in `issuer_codes9.txt` (79 letter segments seen at least twice in the listings of
  batches 1–8; typos seen once, such as "UBTVVQH15" and "QD", are left out) when the other's is not.
  A Đ/D difference that the list does not settle keeps Vision's spelling, as `merge_d`. Anything
  else abstains.
- **B.** Rule B skips accepts whose part after the last "/" contains UBND or HĐND, or is a bare
  National Assembly code such as "QH15": laws (93–99/2025/QH15) and resolutions
  (205–207/2025/QH15) are numbered apart, and in-sample B dropped 7 correct rule-L accepts in
  batches 7–8 for that reason. "UBTVQH" tails stay in B. Set after seeing those 7: in-sample.
- Rule A and the authentication-block path are unchanged.

In-sample (batches 1–8, reads already made; truth = listing except `adjudication.json`; the rule-L
gains were never adjudicated, so their truth is the listing): IN_SAMPLE.
- On the 137 last pages of QH/UBTVQH documents with no date on page 1: Vision finds the sentence on
  98; its date equals the listing on 97 (the other: year 2023 for 2025). Qwen agrees with Vision on
  97; on none do both agree on a date the listing does not have.
- v8 → v9 accepted: batch 1 161 → 161, batch 2 162 → 165, batch 3 248 → 249, batch 4 397 → 418,
  batch 5 323 → 336, batch 6 322 → 326, batch 7 347 → 371, batch 8 313 → 358 (71.6%). In all:
  2,273 → 2,384; gains: L 76, T 19, the narrowed B 16; no v8 accept lost; 0 wrong against the page.
- The 98 sentences give 76 accepts. The rest: Vision's page-1 candidate is not Qwen's number,
  mostly a number cited in the preamble ("203/2025/QH15") (14); no candidate (5); rule A (2); the
  emblem, 244 days (1).
- **Coverage risk, stated before the run:** v9 is under 70% on batches 5 (67.2%) and 6 (65.2%). Its
  gains depend on how many laws and UBTVQH resolutions the batch holds. Batch 9 is older (pages
  146 onward, early 2025 and before); its mix is not known.

v9 is frozen as of the commit that adds this section: `run_scans.py`, `issuer_codes9.txt`,
`passed_prompt.txt`, `header_prompt.txt`, `vlm_ocr.py`, the model and the 1240 px scale. Only input
paths may change.

**Data.** Pages 146 onward of the listing on vanban.chinhphu.vn as of 2026-11-27, read with the
batch-8 lister. Any document whose number is in the listings of batches 1–8 (downloaded or not) is
skipped. First PDF at most 5 MB, in listing order, until 500 PDFs are downloaded. Qwen reads every
`head_small.png` (`header_prompt.txt`), every `auth7_small.png`, and the `plast_small.png` of every
document `--passed-paths` lists (page 1 has no date and Vision finds the sentence).

**Truth: the page, read blind, with no person involved.** As batch 8. All reads are by the agent
that built v9; it sees an image and nothing else: no engine read, no listing value.
- Every v9 or v8 accept that disagrees with the listing (`--to-adjudicate9`) is read from the
  image the accept came from (the full header; `auth7.png`; for rule L, the header for the number and
  `plast.png` for the date) and written to `adjudication.json`. If the image cannot be read with
  certainty, the listing stands.
- Spot check (`--spot9`): every v9 accept from the block or from the last page that agrees with the
  listing, and 100 v9 accepts from page 1 that agree with it, drawn by
  `random.Random(20261201).sample`. Read as batch 8; rule-L accepts are read from the header (number)
  and the last page (date). Into `spot_check.json`, with the negative control of batch 8 (the reads
  moved to the wrong ids must be flagged). A mismatch is looked at again, zoomed in, knowing only
  that there is a mismatch. A confirmed read goes into `adjudication.json` and counts as an error.

1. **Primary.** v9, wrong against the page among accepted, with its 95% upper bound. GO if ≤ 3%;
   KILL v9 if > 5%; ITERATE in between.
2. **Coverage.** Accepted share ≥ 70%.
3. **Certificate.** On this batch alone, never pooled. Binomial test at α = 1%, δ = 0.1
   (n ≥ 230).
4. **Report only.** v8 on the same documents; v9 gains over v8 and losses, with their errors;
   accepts by rule L and from the block, with their errors; rule B drops under v8 and v9; scans
   versus PDFs; VBHN, National Assembly documents, the rest; errors against the listing as
   published; reader errors in the spot check.
