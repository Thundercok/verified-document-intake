# Step 4: real-OCR pilot and a certified gate

Step 3 measured the verifiers against *simulated* OCR noise. This pilot replaces the simulation
with real engines reading rendered images, and asks the question the system exists for: **can a
gate auto-accept a share of fields with a certified error rate, and do the verifiers make that
share larger?**

Numbers: [RESULTS.md](RESULTS.md). Risk–coverage curves: [risk_coverage.svg](risk_coverage.svg).

## Setup

| Piece | What |
|---|---|
| Dossiers | 2000 synthetic dossiers (`render.py`, seed 20261124): one person + one invoice each, from `document_intake.synth` |
| Crops | 13 field crops per dossier. Side A (card / invoice): 9 print fonts. Side B (hand-filled form): 11 handwriting-style fonts. Half the dossiers degraded like a phone photo (tilt ±2°, blur, uneven light, sensor noise, JPEG 35–75) |
| Engines | Apple Vision (`vision_ocr.swift`, `.accurate`, `vi-VT`, language correction on) and Tesseract 5 LSTM with `vie` from tessdata_best (`tesseract_ocr.py`, `--psm 7`) on all crops; Qwen3.5-4B (MLX 4-bit, greedy, `vlm_ocr.py`) on the first 250 dossiers |
| Units | One per dossier per stratum: `name`, `date`, `cccd`, `address`, `amount`, `mst`, `sex`, `place` (`analyze.py: STRATA`) |
| Split | Dossiers shuffled, 60% calibration / 40% held out. Dossiers 0–19 excluded everywhere: they were inspected while two normalisers were fixed (below) |

The crops are plain text lines on a blank background. They imitate no official layout, emblem or
security feature, and every value is generated.

### What counts as an error

As in step 3, an error is semantic: the field's *value* is wrong, not merely its spelling. The value
is what the system would emit: a name key, a parsed date, the digits of an identifier, a parsed
address (canonical province), the amount parsed from the digits, the canonical sex and province.
"Tinh Ninh Bình" is therefore not an error for a place of birth (it resolves to ninh bình), while
"Phan Đinh Phùng" for "Phan Đình Phùng" is.

A unit is wrong if any value it emits is wrong. Pairs emit both copies (`name`, `date`, `cccd`,
`address`); `amount` emits the digits and uses the words only as evidence; `sex` and `place` are
checked against the card number.

### The gate

Mondrian selective risk control at α = 1%, δ = 0.1, one gate per stratum:

- For a threshold λ, the accepted units are those whose score is ≥ λ. Among the n accepted, the
  errors are Binomial(n, R_sel(λ)), so `BinomCDF(k; n, α)` is a p-value for H: R_sel(λ) > α.
- The thresholds form a fixed grid chosen before seeing data (one threshold for score-free systems,
  ten for scored ones), tested with Bonferroni at δ/|grid|. With probability ≥ 1 − δ no certified
  threshold has selective risk above α, so taking the certified threshold with the most
  calibration coverage keeps the guarantee. If none is certified, the stratum accepts nothing.
- Fixed-sequence testing (strict → loose), the usual LTT choice for monotone risks, does not fit
  here: the strictest thresholds accept too few units to reject anything, so the sequence would
  stop at its first step.
- Units in one stratum come from different dossiers and are independent. Pooling strata would mix
  dependent units and, as §4 of the results shows, hide strata that break α.

Systems compared (`analyze.py: SYSTEMS`): engine confidence alone; verifier alone (MATCH);
verifier + confidence; verifier + agreement between two engines.

## Fixes made during the pilot

Inspecting the first 20 dossiers turned up two normalisers that treated harmless misreads as errors,
so the verifiers raised false alarms on correct values:

1. `parse_number_words` rejected a mis-toned currency suffix ("đông", "chăn", "chắn"). Suffixes
   carry no amount, so `đồng` and `chẵn` are now also recognised after diacritic folding. Number
   words are not folded: "mười"/"mươi" and "năm"/"nam" would collide.
2. `resolve_province` did not strip a mis-toned "Tỉnh" ("Tinh", "Tính"). The province prefixes are
   now matched after folding; no province name begins with a word that folds to one of them.

Both have tests. Step 3's results were regenerated after the fixes (`audits/verifier_eval/RESULTS.md`);
they move by at most a few tenths of a point.

## Reproduce

```bash
uv run python audits/ocr_pilot/render.py --n 2000
swiftc -O audits/ocr_pilot/vision_ocr.swift -o audits/ocr_pilot/work/vision_ocr
python3 -c "import json; [print(json.loads(l)['path']) for l in open('audits/ocr_pilot/work/crops.jsonl')]" > audits/ocr_pilot/work/paths.txt
audits/ocr_pilot/work/vision_ocr --jobs 4 < audits/ocr_pilot/work/paths.txt > audits/ocr_pilot/work/vision.jsonl
uv run python audits/ocr_pilot/tesseract_ocr.py audits/ocr_pilot/work/paths.txt audits/ocr_pilot/work/tesseract.jsonl
uv run --group vlm python audits/ocr_pilot/vlm_ocr.py audits/ocr_pilot/work/paths_vlm.txt audits/ocr_pilot/work/vlm.jsonl
uv run python audits/ocr_pilot/analyze.py --md audits/ocr_pilot/RESULTS.md --svg audits/ocr_pilot/risk_coverage.svg
```

`paths_vlm.txt` is the crops of dossiers 0–249. Tesseract needs `data/tessdata/vie.traineddata`
(tessdata_best); the VLM needs `mlx-community/Qwen3.5-4B-MLX-4bit` in the Hugging Face cache.
Generated images and OCR outputs live in `audits/ocr_pilot/work/` (gitignored).

## Limits

- **Rendered, not scanned.** Handwriting-style *fonts* are not handwriting: every glyph of a font is
  identical, letters never touch the way pen strokes do, and the photo degradation is a model.
  Error rates on real forms will differ, probably upward for side B. The pilot measures the gate's
  machinery on real engine behaviour; it is not an estimate of field accuracy on real dossiers.
- **One unit per field crop.** Real intake must also find the field (layout, key–value linking);
  errors there are outside this pilot.
- **Synthetic value distribution.** Names, addresses and amounts come from small pools; real
  distributions have a longer tail (rare names, unusual addresses) where OCR and verifiers both do
  worse.
- **The VLM subset is small.** 230 usable dossiers give 138 calibration units per stratum, fewer
  than the 230 that a zero-error certificate at α = 1% needs, so Qwen systems cannot certify
  anything here whatever their accuracy. Their rows are reported for accuracy and empirical risk.
