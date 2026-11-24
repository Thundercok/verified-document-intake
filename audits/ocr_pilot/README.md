# Step 4: real-OCR pilot and a certified gate

Step 3 measured the verifiers against *simulated* OCR noise. This pilot replaces the simulation
with real engines reading rendered images, and asks the question the system exists for: **can a
gate auto-accept a share of fields with a certified error rate, and do the verifiers make that
share larger?**

Numbers: [RESULTS.md](RESULTS.md), fresh confirmation batch [RESULTS_confirm.md](RESULTS_confirm.md). Risk–coverage curves: [risk_coverage.svg](risk_coverage.svg).

## Findings

Held-out: 792 dossiers. α = 1%, δ = 0.1. Coverage is the share of held-out units the certified
gate accepts. Cells without an error count had **zero** accepted errors on the held-out split.

| Stratum | Tesseract confidence | Tesseract verifier | Vision verifier |
|---|---:|---:|---:|
| name | — | — | — |
| date | — | 35.1% | **85.6%** |
| cccd | — | 31.4% | **93.4%** |
| address | — | — | — |
| amount | 91.7% (2 errors) | 32.6% | **73.9%** |
| mst | 92.0% (6 errors) | 96.5% (4 errors) | **99.6%** |
| sex | — | 59.3% | **88.6%** |
| place | — | 52.0% | **96.6%** |

1. **Confidence alone certifies almost nothing.** Tesseract's confidence works only for printed
   digits (`amount`, `mst`). Apple Vision reports confidence 1.0 on 99.6% of the crops it reads
   (the rest get 0.3 or 0.5), so it carries almost no information. Agreement among Vision's alternative readings certifies only `mst`,
   which is nearly error-free anyway.
2. **Verifiers turn a mediocre engine into a certifiable one.** With Vision, six of eight strata
   reach 74–99.6% coverage at zero held-out errors, although the base error rates are 14%
   (`date`), 11% (`sex`) and 6% (`cccd`). Even Tesseract, wrong on about 58% of handwriting-style
   crops, certifies five strata with zero held-out errors on its verifier.
3. **Real OCR makes the same mistake on both documents.** Step 3 assumed that wrong values shared
   by both copies come from the source. Real OCR makes them itself, and systematically: the same
   engine drops the same tone mark on the printed card and on the handwritten form ("Thụy"/"THUỴ" →
   "Thuy", "Trần" → "Trân", "Nguyễn" → "Nguyên", "Đỗ" → "Đô", "Ấp" → "Áp"). Of the 27 errors the Vision
   verifiers accepted, 21 are names and 6 are addresses, all of this kind (Tesseract: 36 names, 7
   tax codes, 2 places). This is why `name` and
   `address` cannot be certified by comparison alone. Comparison cannot see the error, so the
   evidence must come from outside the pair; see *The lexicon check* below.
4. **Engine errors are correlated, too.** Vision and Tesseract are wrong on the same crop 2.4× as
   often as independence predicts, and in 158 of 2,681 shared misses they produce the same wrong
   value. Requiring the two engines to agree costs coverage (e.g. `date` 85.6% → 35.2%), buys nothing
   where the Vision verifier already had zero held-out errors, and still certifies neither `name`
   nor `address`.
5. **Stratify.** A single pooled threshold (Tesseract verifier + confidence) meets 0.8% risk
   overall while the `name` stratum runs at 6.9%.
6. **Scores cost samples.** A score-free verifier tests one threshold (230 error-free calibration
   units certify 1%); a scored system tests ten at δ/10 and needs 459. Tesseract verifier +
   confidence therefore certifies *less* than the verifier alone (`date`, `cccd`, `amount`,
   `place`).

**Qwen3.5-4B** (230 usable dossiers, too few to certify anything at α = 1%; see Limits) is the most
accurate engine on handwriting-style crops (8.4% / 11.0% semantic errors clean / photo, against
17.7% / 19.1% for Vision) and slightly worse on printed ones (6.1% / 6.7% against 4.8% / 5.4%). It
writes the "đ" currency sign as "d", which the digit parser rejects (`amount` base error 16.8%).
Its accepted errors are of another kind. Of 9 wrong names that its verifier matched, the lexicon
flags only 2 ("Đồ" for "Đỗ", "Tuần" for "Tuấn"). The other 7 are valid names replaced by more
common valid names ("Phượng" → "Phương", "Thúy" → "Thủy"), read the same way on both copies. One
address had its province "Hòa Bình" replaced by "Hà Nội" on both copies. A language model's
prior pulls a reading towards a *plausible* value, which is exactly what a typicality check
cannot see. OCR errors are implausible (a lexicon catches them); VLM errors are plausible (it does
not). The two engines also fail together more often than Vision and Tesseract do (lift 3.7 against
2.4).

## The lexicon check

Finding 3 says that the missing evidence for `name` and `address` is what Vietnamese names and
address words usually are. `src/document_intake/verify/lexicon.py` adds that evidence with one
rule, the *near miss*: a word that is not in the lexicon but folds (diacritics stripped) to a word
that is. "Trân" as a surname folds to "tran", whose only surname is "Trần". "Thuy" folds to the
given names Thùy/Thúy/Thủy/Thụy and is none of them. "Áp" before a number folds to the unit word
"Ấp". A near miss gives UNDETERMINED, so the unit goes to review.

- **Position decides the list.** The first syllable is checked against ~110 surnames; the others
  against ~300 middle and given names. "Lê Bảo Trân" and "Nguyễn Thảo Nguyên" are typical, but
  "Trân Đức Dũng" is not.
- **Unknown words are not judged.** A word with no folded neighbour (a rare or foreign name) passes,
  so the check never penalises a name for being unusual. For address words, only those before a
  number are judged ("Tô 5" is a near miss of "Tổ"; "Tô Hiến Thành" is a street).
- **Independent of the generator.** The lists are general knowledge, not the synthetic pools.
  They contain all 14 generator surnames and every generator given or middle name except "Khỏe"
  (`tests/test_verify_lexicon.py` pins this).

On the main batch (same split as above):

| | name | address | accepted errors caught |
|---|---:|---:|---:|
| Vision verifier | — | — | |
| Vision verifier + lexicon | **63.8%** (2 errors, risk 0.4%, UB 1.2%) | **25.3%** | 25 / 27 |
| Tesseract verifier | — | — | |
| Tesseract verifier + lexicon | **30.6%** | — | 36 / 45 (all 36 name errors) |

The other strata are unchanged, because the check applies only to names and addresses. On units
that the verifier matched and that were correct, the check raised no false alarms. That zero
reflects the synthetic pool, which holds only common names; it is not an estimate for real
records, where surnames such as "Nguyên" or given names such as "Thuy" exist. Those would go to
review, costing coverage but not risk. The two Vision errors left are "Thụy" read as "Thúy"
(another valid name; no lexicon can see this) and "Khoe" (not in the lexicon).

The rule was designed after reading the accepted-error list above, which spans held-out dossiers,
so these numbers are not a clean held-out estimate. To check them, a fresh batch of
1000 dossiers with a seed nobody had looked at (`render.py --seed 20261125`, Vision and Tesseract,
same 60/40 split, [RESULTS_confirm.md](RESULTS_confirm.md)) was run after the rule was frozen:

| Fresh batch, `name` stratum | Matched units | Wrong | Held-out coverage | Held-out errors |
|---|---:|---:|---:|---:|
| Vision verifier | 654 | 9 | — | — |
| Vision verifier + lexicon | 646 | 1 | **64.5%** | 0 (UB 1.2%) |
| Tesseract verifier | 342 | 16 | — | — |
| Tesseract verifier + lexicon | 326 | 0 | — (198 calibration units < 230) | — |

The result replicates for names: the check removes 8 of 9 Vision errors and all 16 Tesseract
errors, and Vision `name` certifies at the same coverage as on the main batch. The one error left
is again a valid name read as another valid name ("Thúy" for "Thủy"). `address` is not certified
on the fresh batch even with the lexicon, but for lack of samples, not because of errors: the
Vision verifier matched 272 addresses with zero errors, yet only 159 of them are in calibration,
fewer than the 230 needed. The fresh batch happened to contain no "Áp" misread.

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
# fresh confirmation batch: render.py --n 1000 --seed 20261125 --out audits/ocr_pilot/work_fresh, the same two OCR
# commands on its paths.txt, then:
uv run python audits/ocr_pilot/analyze.py --work audits/ocr_pilot/work_fresh --skip-below 0 --md audits/ocr_pilot/RESULTS_confirm.md
```

`paths_vlm.txt` is the crops of dossiers 0–249. Tesseract needs `data/tessdata/vie.traineddata`
(tessdata_best); the VLM needs `mlx-community/Qwen3.5-4B-MLX-4bit` in the Hugging Face cache.
Generated images and OCR outputs live in `audits/ocr_pilot/work/` and `work_fresh/` (gitignored).

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
- **The VLM subset is small.** 230 usable dossiers give 135 calibration units per stratum, fewer
  than the 230 that a zero-error certificate at α = 1% needs, so Qwen systems cannot certify
  anything here whatever their accuracy. Their rows are reported for accuracy and empirical risk.
