# Verifier-coverage audit (2026-11-20)

**Question.** The thesis in [docs/RELATED_WORK.md](../../docs/RELATED_WORK.md) §6 says that deterministic verifiers (checksums, digits↔words, arithmetic, CCCD cross-fields, gazetteers) can make certified selective extraction non-vacuous. That only works if verifiers reach enough fields. Go threshold: **≥40% of critical fields** (names, dates, IDs, tax codes, amounts, addresses).

**Verdict: NO-GO for single-form verifiers as the paper's main contribution.** Under any defensible rule, critical-field coverage is **16.5–23.3%**. It reaches 70% only under the liberal rule, which counts "the surname is in a list" as a verified name.

| Rule | All text fields | Critical fields | Go? |
|---|---:|---:|---|
| conservative (strong only) | 10.5% | 16.5% | NO-GO |
| combined (strong, or ≥2 distinct partial/medium) | 14.2% | 23.3% | NO-GO |
| liberal (any non-weak) | 57.1% | 69.9% | GO (overstated) |

Full tables: [RESULTS.md](RESULTS.md). Regenerate with `python3 audits/verifier_coverage/audit.py --md audits/verifier_coverage/RESULTS.md`.

## What the numbers say

1. **Verifiers work where documents carry their own redundancy.**
   - Hóa đơn GTGT: 69% of critical fields (arithmetic, digits↔words, MST checksum).
   - Giấy nộp tiền NSNN: 56%.
   - Giấy ủy quyền: 41% (the agent's name is written 6 times).
2. **Civil and identity forms get almost nothing.** CT01, CC01, TK1-TS, tờ khai xác nhận hôn nhân and sơ yếu lý lịch score 0–10% on critical fields.
3. **The bottleneck is three types:** person names (23 fields), dates (27) and addresses (17).
   - CCCD fixes only the *year* of a date of birth, not the day or month.
   - A surname list checks 1 of about 3 syllables.
   - A gazetteer checks only the administrative tail of an address.

   These are also the fields most likely to be handwritten.
4. **Strong verifiers are fully localised.** Every field with one sits on a form with deliberate redundancy: a table total, an amount in words, or a tax code.

## Caveats (each could move the number)

- **Sample:** only 8 templates. The birth-certificate (khai sinh) and marriage-registration (kết hôn) forms are published only as images, and hoatieu.vn / thuvienphapluat.vn returned 403. The birth certificate is known to write the date of birth in both digits and words, so adding it would raise date coverage on that form.
- **Extraction quality:** sơ yếu lý lịch comes from a model-extracted page summary. Hóa đơn comes from the legal list of mandatory contents, not a blank form.
- **Annotation is manual.** Hints (`words_pair`, `arith`, `cccd_cross`, `repeat_copy`, `cccd_province`) are hand-annotated in `forms/*.toml` and open to review. CCCD cross-checks assume the ID shown is a CCCD; it may be a passport.
- **Counting:** table columns are counted once, not once per row. This understates the weight of verifiable money columns on long invoices and of the household-member rows on CT01.
- **Rules not yet implemented:** checksums are assumed from python-stdnum (MST). The CCCD structure follows Nghị định 137/2015 and Thông tư 07/2016. None of the verifiers has been run on real OCR output yet.

## Implication for the paper

The single-form version of "hard verifiers make certification non-vacuous" fails on the documents that matter most (civil and identity forms). Two directions survive the audit:

- **A. Dossier-level redundancy (audited below).** Administrative procedures take a *hồ sơ* (dossier), not a single form. If the dossier also contains a printed anchor document (CCCD card, existing birth certificate, previous trích lục), then the handwritten name, DOB, ID and address on the form can be cross-checked against high-accuracy printed OCR. That would hit exactly the three bottleneck types.
- **B. Verifiers as one signal, not the thesis.** Keep the verifier library as a feature family inside a learned confidence model, as in 2609.20110, and make the contribution the Vietnamese handwriting and on-device benchmark. This is safer but less novel.

---

# Direction A audit: dossier-level cross-document verifiers (2026-11-20)

**Question.** For each of the 8 forms, which procedure does it belong to, which other documents reach the system with it, and which form fields can those documents check? Encoded in [dossiers.toml](dossiers.toml); computed by the same `audit.py` (section "Direction A" of [RESULTS.md](RESULTS.md)). Same 103 critical fields, same rules, same ≥40% threshold.

An anchor counts as **strong** when it states the field in full and must match (`exact`). It counts as **partial** when it states the field in full but may legitimately differ (`may_differ`: the person moved, the card is older than the form). The card's print and its chip count as one source, not two.

**Verdict: GO, conditional on the deployment scenario.**

| Scenario | What is reachable | Critical (combined) | w/o signing dates | Go? |
|---|---|---:|---:|---|
| `single_form` | the form alone | 23.3% | 26.7% | NO-GO |
| `archived_min` | paper backlog, legally required dossier parts + public MST registry | 37.9% | 43.3% | NO-GO (borderline) |
| `archived_typical` | + customary copies (CCCD and khai sinh in job dossiers) | **47.6%** | 54.4% | GO |
| `live_scan` | counter intake that photographs the presented card / tax notice | **64.1%** | 73.3% | GO |
| `live_chip` | + NFC chip read | 65.0% | 74.4% | GO |
| `gov_db` | agency with CSDL dân cư / e-invoice portal access | 76.7% | 85.6% | GO (but see 4) |

Under the conservative rule (strong only): 16.5% single-form, 38.8% archived_typical, 53.4% live_scan.

## What the numbers say

1. **The bottleneck types are fixed, except dates.**
   - Under `live_scan`, names go from 26% to 74%, addresses from 0% to 71% and IDs from 7% to 64%.
   - Dates only reach 33%. Of the 27 critical dates, 13 are signing dates ("ngày … tháng … năm …" next to a signature), which no other document restates. Most of the rest are career-timeline dates on the sơ yếu lý lịch (Đoàn/Đảng admission, education and work periods).
2. **Which forms gain depends on the channel, not on the form.**
   - Giấy ủy quyền gains in the archive (41% → 91%), because the notarial file keeps a copy of each party's ID.
   - Sơ yếu lý lịch gains only through customary copies (0% → 53%).
   - Tờ khai xác nhận hôn nhân (0% → 88%) and TK1-TS (0% → 67%) gain only if the counter photographs the card, because the law says the card is *presented*, not submitted. The portal text explicitly allows the officer to "chụp lại", so capturing it is lawful.
   - CT01 stays at 25% outside `gov_db`. Household-member rows are verifiable only through CSDL dân cư.
3. **The chip adds almost nothing to coverage** (+0.9 points over printed OCR). Its value is trust (an issuer signature, no OCR error), not reach. A camera at the counter is enough for the audit's purposes.
4. **`gov_db` is not a pitch scenario.** An agency that can look a citizen up by ID does not need OCR for identity fields beyond the ID itself. It is reported as an upper bound only.
5. **The versioned gazetteer changes role.**
   - A card issued before 1/7/2025 states an address with a district. A form filled after the merger states it without one.
   - Comparing the two needs an old→new administrative-unit mapping. The gazetteer becomes a *normaliser* for cross-document matching, not just a membership check.

## Caveats specific to direction A

- **Dossier composition comes from secondary sources** (provincial portals, the national DVC portal, law-firm blogs). In particular, the claim that a notarial file keeps ID copies under Luật Công chứng 2024 was not checked against the article text. The law also allows a printout from CSDL dân cư, which would be a printed anchor too. Giấy ủy quyền's 91% rests on this.
- **The job-dossier copies are convention, not law.** `archived_typical` passes the threshold only because of them and the notarial file. `archived_min` alone is borderline (37.9%).
- **Anchor fields from memory.** The parent rows of the giấy khai sinh template and the gender/nationality fields on the new card front were not re-verified. The chip field list comes from a provincial guide, not from a technical spec.
- **`exact` assumes entity linking is solved.** The system must know which card belongs to which person block (requester vs. subject, bên ủy quyền 1 vs. 2). That linking is itself a task and can fail.
- **Ground truth changes meaning.** If a citizen wrote the wrong DOB, the cross-check flags a mismatch and the field goes to a human. That is the right outcome for data quality, but it counts as "abstain" in a pure OCR-accuracy metric.
- **The earlier single-form numbers are slightly optimistic for individuals' tax codes.** Since 1/7/2025 an individual's MST is the 12-digit số định danh (TT 86/2024/TT-BTC), which has no mod-11 check digit. `V_MST_CHECKSUM` applies only to organisations' MSTs.

## Implication for the paper

The publishable thesis moves from the single form to the dossier:

> *Cross-document redundancy in administrative dossiers makes certified selective extraction of handwritten Vietnamese forms non-vacuous.*

The technical core then becomes:

1. **Dossier KIE with entity linking:** which anchor belongs to which person block.
2. **Normalised comparison:** names (case, diacritics, spacing), dates (digits vs. words, `dd/mm/yyyy` vs. "ngày … tháng …"), and addresses across the 2025 administrative merger via the versioned gazetteer.
3. **A certified gate** that treats an `exact` agreement and a `may_differ` agreement differently.
4. An evaluation split by **scenario** (archived vs. live intake), since coverage differs by 16 points between them.

Realistic data sources are notarial archives and HR dossiers (archived), and one-stop counters (live). All of them contain CCCD data, so the benchmark has to be synthetic or consented, kept under `data/private/`, and never committed.
