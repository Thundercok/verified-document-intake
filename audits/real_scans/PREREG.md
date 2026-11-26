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
