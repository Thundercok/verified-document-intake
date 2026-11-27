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

7. **v3 meets its bar on a third batch, and its only errors are in the ground truth
   ([RESULTS_v3.md](RESULTS_v3.md)).** v3 adds a rule ("TT, NĐ, VBHN, TTLT and QH numbers carry a
   /YYYY/ segment", which catches a slash read as "1") and a second read: Qwen3.5-4B reads the same
   header and the document is accepted only if both engines give the same number and date. It was
   frozen and pre-registered (PREREG.md) before 340 unseen documents were listed (positions
   501–1000, 27/08 to 30/09/2026). It accepts 264 (77.6%, bar 70%) and 3 are wrong against the
   listing: upper bound 2.9%, under the 3% bar, so **GO**, by a margin of 0.1 points. Three errors
   in 264 is not a 1% certificate (p = 0.73).
   Looked at **after** scoring, none of the three is a misread. In one, the first PDF is a
   correction letter, not the document listed, and both engines read the letter correctly. In
   one, the page says "ngày 18 tháng 9" and the listing 21/09. In one, the listing's number
   holds a Cyrillic "Т". Scored against the page, v3 would have 0 wrong in 264, which would pass
   the certificate test (p = 0.07). That count is post hoc and is **not** a certificate. What it
   does show is that the publication listing is not an exact side A either: 3 of the 264
   accepted entries (1.1%) disagree with the page they point to.
   The rules alone accept 296 with 5 wrong (upper bound 3.5%); Qwen's disagreement costs 30
   documents that Vision read correctly. Vision's exact match is 92.1% for the number and 92.6%
   for the date (ITERATE for the third time). v2, report only, has 7 wrong of 300 (upper bound
   4.3%). Dropout costs 1.4 points on page 1, between the bars again.

8. **v4, written on all 726 documents (in-sample, not a test).** Of the 169 documents v3
   rejected, 66 were Qwen dropping the stroke of "Đ" ("NĐ" → "ND"), swapping day and month, or
   misreading a digit; 64 were Vision losing the slash ("47 |2026", "472 NQ", "22321QĐ").
   v4 reads every number Vision's text could stand for and accepts only if exactly one passes
   the checks and equals Qwen's read, with "Đ"/"D" and a day-month swap tolerated in Qwen's.
   Two engine errors it then let in were fixed before freezing: a handwritten "142" read as "1H2"
   by both (now rejected, a symbol may not be followed by "/"), and "ngày21tháng" read as day 2 by
   both. For that one the page prints a second date, the e-signature time ("Thời gian ký:
   22.09.2026"); v4 abstains when the issue date is not 0–14 days before it (the gap is 0–14
   days for 90% of the 469 dev pages that print it). In-sample, v4 accepts 574 of 726 (79.1%; v3
   560) and is wrong on 0 against the page. Its 3 disagreements with the listing are listing
   faults, checked on the page image (not blind: the engines' reads had been seen). Re-reading
   rejections with Qwen at full resolution recovers 23 more but lets in "2223" read as "2023" by
   both engines, so it is report-only. Batch 3 alone would pass the certificate test (247
   accepted, 0 wrong, p = 0.08), but v4 was written on batch 3: **this is not a certificate.**
   The cost of the emblem rule falls on consolidated texts, which are published weeks after
   issue: on batch 3, v4 accepts 72.6%, close to the 70% bar.

9. **v4 passes on a fourth batch, and the certificate test passes by a small margin
   ([RESULTS_v4.md](RESULTS_v4.md)).** v4 was frozen and pre-registered (PREREG.md) before 500
   unseen documents were listed (positions 1001 onward, 16/06 to 27/08/2026). Truth was the page:
   the two accepted documents that disagreed with the listing were read from the header image alone,
   without the engines' reads or the listing's values. v4 accepts 395 of 500 (79.0%, bar 70%), and
   1 is wrong against the page: upper bound 1.2%, so **GO**. The certificate test passes (p = 0.094
   against δ = 0.1). One error needs at least 388 accepted documents, and 395 were accepted. As
   pre-registered, the claim is this: on central government documents published on this site in this period,
   v4's accepted number-and-date pairs are wrong at most 1% of the time, with 90% confidence.
   The one error is not a misread digit. Vision read "1279/QD-TTg" and Qwen read "1279/QĐ-TTg". v4
   tolerates "Đ"/"D" in Qwen's read, so the two agreed, and v4 output Vision's spelling without the
   stroke. A search for "QĐ" would miss the record. Taking the "Đ" from either engine fixes this,
   but the fix was written after scoring, so it needs another batch.
   Coverage splits by source: 72.4% on the 323 scans (the one error is a scan) and 91.0% on the 177
   PDFs with a text layer. The full-resolution re-read (report only) brings coverage to 409, with no new
   error. One of the documents it adds has a listing fault: the listing says 21/08 and the page says
   11/08. Vision's exact match is 91.8% for the number and 90.0% for the date (ITERATE for the
   fourth time), and the format checks alone let 15 of 423 wrong reads through (upper bound 5.4%).
   Dropout costs nothing on this batch (+0.4 points).
   **Limits of this result.** The reader who adjudicated is the same agent that built v4. That
   reader saw no reads or listing values, but it is not an independent person. The certificate holds
   for this site and period only, not for commune paperwork or phone photos.

10. **Blind spot check: 0 hidden errors in 100 (pre-registered, PREREG.md).** Batch-4 truth was the
    listing wherever v4 agreed with it, so a listing fault that both engines reproduce would go
    unseen. 100 of the 394 such documents (61 scans) were drawn with a fixed seed and read blind
    from a band of the header image. 100 of 100 match the listing and v4, with no field marked
    unreadable and no mismatch for the reader to withdraw. So the certificate stands. This check
    could only have falsified it: 0 of 100 still allows hidden errors in up to 3.0% of agreeing
    documents (one-sided 95%). The reader is the same agent as before.
    Seen after scoring: two of the 100 listing entries spell "NĐ-CP" with a Cyrillic "Р". Across all
    four listings, 15 of 1,792 entries (0.8%) contain a Cyrillic letter. A plain string match against the listing
    would count those as errors, and the scoring handles them by mapping the letters to Latin. In
    all 100, v4's output matches the page exactly, including "Đ".

11. **v5 on a fifth batch: risk passes, coverage misses (pre-registered, PREREG.md).** 500 documents
    not seen before (04–06/2026). No person took part: every read was done blind by the agent that
    built v5. v5 accepts 328 (**65.6%, below the 70% bar**), 0 wrong against the page, upper bound
    0.9% → **GO** on risk. The certificate passes on this batch alone (p = 0.037, n = 328 ≥ 230).
    The blind spot check read 100 random agreeing accepts from the page: 0 hidden errors, no field
    unreadable. Three negative controls (a changed digit, a changed day, rows shifted by one)
    were each flagged 100 of 100 by the comparison, so a match is not an artefact of the script.
    Up to 3.0% of the 227 unsampled agreeing accepts could still hide an error.
    **The Đ fix was not exercised.** v5 and v4 give the same output on all 500 documents: Vision
    kept the stroke in all 187 accepted numbers that contain "Đ", so `merge_d` never fired. This
    batch is evidence that v4/v5 holds, not evidence that the Đ rule works.
    **Why coverage fell (seen after scoring, not a test).** 81 of the 500 are consolidated texts
    (VBHN) whose page 1 has no "Số:" line and no place-date line. v5 abstains on all 81, which is
    the right behaviour, but the bar counts them. In batch 4, 34 of 52 consolidated texts were
    accepted, so this batch has a different consolidated template. Without them, coverage is
    78.3% (328 / 419). This number was computed after the result and does not rescue the bar.
    Scans: 73.9% accepted (batch 4: 72.4%). PDFs with a text layer: 45.1% (batch 4: 91.0%), which
    is the same consolidated-text effect, since 70 of the 81 are PDFs.
    **The listing.** The one adjudicated document is a listing fault: the listing writes "QD-UBND",
    and the page and v5 write "QĐ-UBND". This is the mirror image of v4's batch-4 error.
    Vision alone, all 500: number 77.0%, date 77.8% exact (scans 87.9% and 89.0%); the format
    checks let 78 of 439 wrong reads through (upper bound 21.0%), mostly consolidated texts where a
    date quoted in the title is taken as the header date. Dropout costs 0.4 points.
    **Scope.** 494 of the 500 are central government documents. 6 are provincial decisions
    (UBND), all 6 accepted, all correct. That is too few to say anything about provinces.

12. **v6 on a sixth batch: risk passes, coverage passes by one point (pre-registered, PREREG.md).**
    500 documents not seen before (02–03/2026). v6 is v5 plus two changes made after batch 5: a VBHN
    number may lack the year ("37/VBHN-BXD"), and when page 1 gives nothing, the VBHN
    authentication block ("XÁC THỰC VĂN BẢN HỢP NHẤT") is found in the text layer, cropped and
    read by Vision and Qwen like a header. No person took part. v6 accepts 355 (**71.0%**, bar
    70%), 0 wrong against the page, upper bound 0.8% → **GO**; certificate p = 0.028 → certified.
    v5 on the same documents: 324 (64.8%), 0 wrong; it would have missed coverage again.
    **The margin is thin.** The 95% interval for coverage is 66.9–74.8%, so the next batch can
    miss the bar with no change in the method. Of the 31 extra accepts, all 31 come from the
    authentication block; the relaxed year rule added none on page 1.
    **Consolidated texts are still mostly lost.** 107 of the 500 are VBHN; v6 accepts 31 (29.0%),
    all correct. The block was found in 39 of them; 8 of those 39 were rejected. 9 VBHN are scans,
    where v6 cannot look for the block. Seen after scoring, not a test: of the 59 text-layer VBHN
    where no block was found, 21 hold both "XÁC THỰC" and "HỢP NHẤT" somewhere in the text, but
    not in the order or spacing `auth_locate` looks for; 22 hold neither.
    Without VBHN, v6 accepts 82.4% (324 / 393). Scans 79.4%; PDFs with a text layer 46.5%.
    **Truth.** All 355 accepts agree with the listing, so nothing was adjudicated. The blind spot
    check read 100 random accepts (86 from the header band, 14 from the block crop): 0
    mismatches; reads paired with the wrong id were flagged 100 of 100. Up to 3.0% of the 255
    unsampled accepts could still hide an error. The reader is the agent that built v6.
    Vision alone, all 500: number 73.6%, date 75.0% (scans 91.2% and 92.8%). The format checks let
    116 of 470 wrong reads through (upper bound 28.2%), worse than batch 5, again mostly VBHN
    title dates. Dropout costs 0.6 points.

**What this means for the plan.** Printed administrative documents are within reach of Apple
Vision, but their key fields carry handwriting or an overlay, and Vision's misreads there are
plausible numbers. The design that holds up is the one the verifier already assumes: compare
against an exact side A (here the issuing register or the publication listing, for a CCCD the QR
code) rather than trust a single read. Red dropout can stay in the pipeline; it costs nothing
measurable. On the third batch, two engines that agree reached an upper bound of 2.9% on their
own, and their remaining disagreements with the listing were the listing's fault. The open
problem moves from reading to checking: a side A that is itself wrong about 1% of the time cannot
certify 1%. On the fourth batch, scored against the page, v4 passed the 1% certificate test,
pre-registered, with one error, which came from writing "Đ" as "D" rather than from a misread digit.
The test passes for documents from the central government, and only 72% of scans are accepted.
On the fifth batch, v5 passed the certificate again (0 wrong in 328) but missed the coverage bar,
because consolidated texts carry no number on page 1. Reading their number from elsewhere is the
next coverage gain; the risk side has now held on two batches in a row. On the sixth batch, v6
read that number from the authentication block and passed both bars, coverage by one point: the
risk side has held on three batches, coverage only just.

## Not tested here

- **The signer's name under the seal.** No ground truth.
- **Phone photos.** These are flatbed scans and rendered PDFs.
- **Commune-level documents.** Of 2,226 documents, all but 6 provincial ones come from central
  government; commune paperwork may be older, fainter and more often handwritten.
- **The number of a scanned consolidated text (VBHN).** v6 finds the authentication block only
  through the text layer; in a scan it abstains. Batch 6 had 9 such scans.
- **The body text.** Only the header and the signer block were read.

## Reproduce

```bash
swiftc -O audits/real_scans/render_pages.swift -o audits/real_scans/work/render_pages
# PDFs in data/private/vbcp/pdf/<listing index>.pdf, listing in data/private/vbcp/docs.json
# Tesseract needs data/tessdata/vie.traineddata (tessdata_best), as for the pilot
uv run python audits/real_scans/run_scans.py --md audits/real_scans/RESULTS.md
# confirmation batch: PDFs in data/private/vbcp2/pdf/, listing in data/private/vbcp2/docs.json
VBCP_DIR=data/private/vbcp2 uv run python audits/real_scans/run_scans.py --confirm --md audits/real_scans/RESULTS_confirm.md
# third batch (v3): render, then Qwen on the 1240 px header crops, then score
#   paths file = one data/private/vbcp3/pages/NNN/head_small.png per line
HF_HUB_OFFLINE=1 uv run --group vlm python audits/ocr_pilot/vlm_ocr.py paths.txt data/private/vbcp3/qwen.jsonl \
    --prompt-file audits/real_scans/header_prompt.txt --max-tokens 96
VBCP_DIR=data/private/vbcp3 uv run python audits/real_scans/run_scans.py --confirm3 --md audits/real_scans/RESULTS_v3.md
# fourth batch (v4): Qwen as above into data/private/vbcp4/qwen.jsonl, then OCR and the ids to adjudicate
VBCP_DIR=data/private/vbcp4 uv run python audits/real_scans/run_scans.py --to-adjudicate
#   report-only stage 2: same Qwen command on the full-resolution head.png of rejections whose
#   date reads, passes the e-signature check and has a candidate passing the checks -> qwen_full.jsonl
#   then rerun --skip-ocr --to-adjudicate; read each listed head.png blind into adjudication.json
VBCP_DIR=data/private/vbcp4 uv run python audits/real_scans/run_scans.py --skip-ocr --confirm4 --md audits/real_scans/RESULTS_v4.md
# fifth batch (v5): Qwen as above into data/private/vbcp5/qwen.jsonl, then OCR and the ids to adjudicate
VBCP_DIR=data/private/vbcp5 uv run python audits/real_scans/run_scans.py --to-adjudicate5
#   read each listed head.png blind into adjudication.json; then the spot-check ids:
VBCP_DIR=data/private/vbcp5 uv run python audits/real_scans/run_scans.py --skip-ocr --spot5
#   read the 30-65% header band of each blind into spot_check.json {"id": {number, date}}
VBCP_DIR=data/private/vbcp5 uv run python audits/real_scans/run_scans.py --skip-ocr --confirm5 --md audits/real_scans/RESULTS_v5.md
# sixth batch (v6): run_scans renders and crops the authentication block (auth_small.png) too;
#   Qwen as above on head_small.png -> qwen.jsonl and on auth_small.png -> qwen_auth.jsonl
VBCP_DIR=data/private/vbcp6 uv run python audits/real_scans/run_scans.py --to-adjudicate6
VBCP_DIR=data/private/vbcp6 uv run python audits/real_scans/run_scans.py --skip-ocr --spot6
#   prints id:where; read the header band, or auth.png when where = auth, blind into spot_check.json
VBCP_DIR=data/private/vbcp6 uv run python audits/real_scans/run_scans.py --skip-ocr --confirm6 --md audits/real_scans/RESULTS_v6.md
```
