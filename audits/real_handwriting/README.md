# Step 5: real handwriting

The OCR pilot (`../ocr_pilot`) read handwriting-style *fonts*. This step runs the same engines and
the same address value and verifiers on lines that people wrote by hand, to see which pilot findings
survive. Numbers: [RESULTS.md](RESULTS.md).

## Data

Both sets are public research data. They are kept under `data/private/` (gitignored) and are not
redistributed here; this folder holds code and aggregates only.

| Set | What | Source |
|---|---|---|
| Cinnamon addresses | 1,838 scanned lines, each a Vietnamese address handwritten by a person, with its transcription (Cinnamon AI handwriting challenge, 2018) | zip linked from the README of [TomHuynhSG/Vietnamese-Handwriting-Recognition-OCR](https://github.com/TomHuynhSG/Vietnamese-Handwriting-Recognition-OCR) (code MIT; terms of the data itself not stated) |
| Handwritten prose | 201 handwritten lines of prose, test split | [HenryBui/vietnamese_handwriting_line_ocr](https://huggingface.co/datasets/HenryBui/vietnamese_handwriting_line_ocr) (no licence stated) |

Addresses carry no names or ID numbers. The prose set is used only for raw engine error.

## Findings

1. **Real handwriting is much harder than handwriting fonts.** Apple Vision's character error
   rate is 0.103 on the real addresses and 0.135 on the prose. On the font crops it was 0.029. The
   share of addresses whose parsed value is wrong rises from 39.9% to 83.7%. These are genuine
   misreads ("Quận Hống Đa", "Huyện Trông Ban", "Cầu Diễn" for "Cầu Dền"), not scoring artefacts.
   Repairing misread unit words ("Phương 13") fixes 5 of the 1,538 wrong lines. Tesseract `vie`
   gets no real address right (CER 0.65).
2. **H1 holds on real data.** Vision still reports confidence 1.0 on 99.3% of real lines,
   including the wrong ones. Its confidence says nothing about whether a read is right.
3. **Single-copy signals do not rescue it.** Requiring a parsed province and a clean lexicon check
   still accepts 70% of the lines, at 76.6% risk, and holds back only 36% of the wrong ones.
   Vision and Tesseract never agree on a whole address.
4. **Against an exact card, the comparison accepts few lines.** The CCCD QR code, or a clean print
   read, gives an exact side A. Compared against it, Vision's real handwritten read matches on
   13.4% of the lines. The truth itself would match on 85.4%, so the engine, not the verifier,
   costs the coverage. Zero errors among the matched lines is by construction here (see
   RESULTS.md §2), so this measures coverage only.
5. **Nothing can be certified at α = 1% on a 60/40 split.** The calibration part holds about 150
   matched lines. A zero-error certificate needs 230.

6. **A VLM helps, but not enough.** Qwen3.5-4B read a seeded sample of 200 of these lines. On
   that sample it matches the exact card on 23.5% of lines; Vision matches on 13.0%. The bar set
   before the run was 50%, so Qwen misses it. Accepting a line when either engine matches gives
   30.5%. Qwen still makes the plausible substitutions the pilot found: "xã Bình Hòa Nam, huyện
   Đức Huệ" became "xã Hải Hậu, huyện Đức Hòa", two place names that exist. It also costs about
   5.1 s per line on this Mac, against well under a second for Vision. Many of its remaining
   misses are one tone mark from a real unit name ("Kim Đồng" for "Kim Động"). A gazetteer could
   snap those to the right name, but that is untested.

**What this means for the plan.** The verifier logic is not what failed. On real Vietnamese
handwriting, neither Apple Vision nor a 4B VLM reads well enough for a gate to accept much. The
rule set before the Qwen run says to narrow the scope rather than chase engines. The scope becomes
printed and typed documents plus the CCCD QR code, where the pilot's engines and verifiers work.
Handwriting is reported as a measured limit.

## Not tested here

- **Two handwritten copies compared.** Only 8 addresses occur twice in the set.
- **Field finding on a form.** Each image is already one field line.
- **Stamps, skew or phone photos.** The lines are clean flatbed scans in blue ink.
- **Names, dates and ID numbers.** The set has addresses only.

## Reproduce

```bash
# images: data/private/cinnamon_dl/vn_handwritten_images/{labels.json,data/}; prose: data/private/henrybui_dl/test.parquet
# extracted to data/private/real_hw/henrybui/{img/,labels.jsonl,paths.txt}; Cinnamon paths in data/private/real_hw/cinnamon/paths.txt
audits/ocr_pilot/work/vision_ocr --jobs 6 < data/private/real_hw/cinnamon/paths.txt > data/private/real_hw/cinnamon/vision.jsonl
uv run python audits/ocr_pilot/tesseract_ocr.py data/private/real_hw/cinnamon/paths.txt data/private/real_hw/cinnamon/tesseract.jsonl
# (the same two commands for data/private/real_hw/henrybui)
uv run python audits/real_handwriting/analyze_real.py --md audits/real_handwriting/RESULTS.md
```
