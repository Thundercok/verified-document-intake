# Verifier evaluation on synthetic dossiers (2026-11-21)

**Question.** The dossier audit ([../verifier_coverage/README.md](../verifier_coverage/README.md)) counted how many critical fields a verifier *reaches*. This asks how good each verifier in `src/document_intake/verify/` is as an **error detector**:
- Does it stay silent on correct values written differently?
- Does it catch OCR-like errors?
- Which errors does it let through?

Full tables are in [RESULTS.md](RESULTS.md). Regenerate them (about 40 s) with:

```bash
uv run python audits/verifier_eval/run.py --n 3000 --md audits/verifier_eval/RESULTS.md
```

## Setup

- **Data.** [`document_intake.synth`](../../src/document_intake/synth/) generates synthetic people, invoice amounts and organisation tax codes. Each person's CCCD prefix is consistent with their sex, birth year and birth-registration province. Each person has one residence, written as a pre-2025 address and as a post-2025 address. No value is real.
- **Clean pairs.** Each side is rendered the way a different document writes it:
  - names in capitals or title case, with either tone placement (Hòa/Hoà), sometimes NFD;
  - dates as dd/mm/yyyy, d/m/yyyy, "ngày … tháng … năm …" or fully in words;
  - addresses with full prefixes or abbreviated (P.5, Q.3, TP.HCM), in the same era or across the 2025 reform;
  - amounts in words with the accepted variants (nghìn/ngàn, linh/lẻ, mốt/một, tư/bốn, lăm/nhăm).
- **Errors.** Each error is one OCR-like edit, applied by [`noise.py`](../../src/document_intake/synth/noise.py):
  - tone change, add or drop;
  - loss of the ă/â/ê/ô/ơ/ư/đ diacritic;
  - letter drop, syllable drop or merged words;
  - lăm↔năm or mươi↔mười;
  - a look-alike digit, or a digit deleted, duplicated or transposed.

  An edit counts as an error only if it changes what the field *says*: the name key, the parsed date or amount, the digits, or the address key. Harmless edits are resampled.
- **Conditions.** 3000 units each:
  - `clean`: no error;
  - `err_A`: one edit on side A, the anchor document;
  - `err_B`: one edit on side B, the form;
  - `err_both`: independent edits on both sides;
  - `consistent`: the same wrong value written on both sides. This models an error in the source, or a systematic misread.

## Findings

1. **No false alarms on correct variation.** Every verifier raised 0 alarms on 3000 clean pairs, a rule-of-three 95% upper bound of 0.1%. That covers case, NFD, tone placement, abbreviations, dates in words and number-word variants. It only shows the verifiers tolerate the variation the renderer produces. Real documents vary more.
2. **Cross-document comparison catches independent errors.**

   | Verifier | Recall on independent errors |
   |---|---:|
   | `V_MONEY_WORDS` | 100% |
   | `V_ID` | 99.2% |
   | `V_NAME` | 98.4% |
   | `V_DATE` | 93.6% |

   `V_DATE`'s remaining ~6% are UNDETERMINED, not accepted. Typically an edit removed the day, and a full date is not confirmed by a partial one. At 5% error prevalence, at most 0.1% of what these verifiers accept is wrong.
3. **"Independent" errors still collide.**
   - In `err_both`, `V_NAME` recall drops to 95.3% and `V_ID` to 97.7%, because both sides received the *same* edit. Examples: VÕ→VÓ on the card and on the form; the same diacritic dropped from "Hương" on both.
   - Short strings have few confusable positions, so two independent readers often make the same mistake.
   - Real OCR confusions are more concentrated than this uniform model, so real collisions should be more frequent.
   - Agreement between two documents is therefore weaker evidence than an independence assumption suggests. The gate's risk must be calibrated on real OCR output, not derived from per-side error rates.
4. **Consistent errors are invisible to comparison. Only intrinsic checks see them.** This is the main result.

   | Verifier | Kind | Recall on consistent errors |
   |---|---|---:|
   | `V_NAME`, `V_DATE`, `V_ID`, `V_ADDR`, `V_MONEY_WORDS` | comparison | 0–6.4% |
   | `V_MST` (mod-11 checksum) | intrinsic | 97.2% |
   | `V_WORDS_GRAMMAR` (do the words parse?) | intrinsic | 96.8% |
   | `V_CCCD_FORMAT` | intrinsic | 62.4% |

   Combining the CCCD comparison with the intrinsic CCCD checks raises recall on a wrong number copied identically onto both documents from **0% (`V_ID`) to 51.7% (`V_ID+CCCD`)**. The extra coverage comes from the province code, the century/sex digit and the birth year, checked against the khai sinh. The last six digits have no check digit, which caps this at roughly half.
5. **Address coverage is capped by the 2025 reform.**
   - `V_ADDR` accepts 49.4% of clean pairs. The other 50.6% are written in different eras and come back UNDETERMINED, because the new commune name is not derivable without a gazetteer.
   - That is exactly the share of cross-era pairs generated, so the commune-level table (Công văn 1027/CTK-CSCL) is the largest single lever on address coverage.
   - Of the 3.6% missed address errors, 268/320 are *canonicalisable*: a tone or diacritic edit to a province name resolves through the closed list of 97 names. If the system outputs the canonical name instead of the OCR text, these errors are corrected, not accepted.
6. **CCCD sub-checks each see only their own digits.**

   | Verifier | Recall | What it misses |
   |---|---:|---|
   | `V_CCCD_YEAR` | 83.1% | edits outside digits 4–6, and date edits that keep the year |
   | `V_CCCD_SEX` | 42.9% | as above, plus "Nữ"→"Nu", which the fold-based normaliser tolerates (1755 of 3473 misses are canonicalisable) |
   | `V_CCCD_PROVINCE` | 44.2% | as above |

   They are useful only in combination (finding 4).
7. **MST.**
   - The weights 31, 29, 23, 19, 17, 13, 7, 5, 3 are distinct and non-zero mod 11. Every single-digit substitution and every adjacent transposition in the 10-digit base therefore changes the check, which `tests/test_verify_ids.py` confirms for the check digit.
   - The 3.4% misses sit in the 3-digit branch suffix of 13-digit codes, which has no checksum. Every inspected miss had that form, e.g. `…-825` → `…-875`.
8. **Number-word grammar** misses 3.0%. Every miss is a dropped syllable that leaves a shorter but valid number ("năm mươi lăm" → "năm mươi"). The digits↔words comparison catches these (100%).

## Implications for the gate

- **An intrinsic check (checksum, grammar, CCCD structure) defends against errors that agreement cannot see.** A field confirmed by both a comparison and an intrinsic check deserves more weight than one confirmed by a comparison alone. The audit's "strong" label should depend on that, not on the match kind only.
- **Comparison verifiers trade false alarms for UNDETERMINED.** Their false-alarm rate was 0 in every condition, while the cases they cannot decide come back UNDETERMINED: cross-era addresses, partial dates. Coverage, not precision, is what the gate loses there.
- **Emitting canonical values matters.** For closed-vocabulary fields (sex, province), outputting the canonical value turns tolerated OCR edits from accepted errors into corrections.

## Caveats

- **The noise is synthetic.** Edits are single, uniform over applicable positions, and their real frequencies are unknown. Real OCR makes multi-edit errors, has field- and engine-specific confusion matrices, and makes far fewer errors on the printed anchor than on the handwritten form. Step 4 (pilot with Apple Vision, Tesseract and a ~1B OCR-VLM, gate at α = 1%) replaces this noise with real output.
- **"Consistent" is one model of correlated error:** a wrong value stated identically on both sides. Partially correlated errors (similar but not identical misreads) are not modelled.
- **The 5% prevalence is assumed.** Precision is 100% everywhere only because no false alarm was observed. It is bounded by the renderer's variety, not by the real world's.
- **The generator is narrow.** Name, street and commune pools are small, and addresses use a fixed structure (street, commune, district, province). Unusual layouts make the parser return UNDETERMINED, which this evaluation does not exercise.
