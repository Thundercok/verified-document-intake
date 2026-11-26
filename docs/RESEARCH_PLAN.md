# Research Plan: Selective & Verified On-Device Document Digitization

## 1. Motivation & Research Gap

Low-resource administrative digitization (such as Vietnamese commune/ward civil registry, land, and archival records) operates under three simultaneous constraints that break standard cloud-OCR pipelines:
1. **Hard Privacy:** Citizen identity documents (CCCD, household registries, certificates) cannot be transmitted to external cloud APIs.
2. **Severe Visual Noise:** Red official stamps overlapping printed/handwritten text, skewed flatbed scans, faded carbon copies, and dense Vietnamese diacritics.
3. **Zero-Tolerance Silent Errors:** A single misread digit in a 12-digit CCCD or birth date invalidates downstream records.

Standard on-device OCR engines (Apple Vision, Tesseract `vie+eng`) expose token-level confidence scores that are poorly calibrated under stamp occlusion and diacritic confusion.

---

## 2. Core Research Questions & Falsifiable Hypotheses

- **RQ1 (Calibration under Administrative Noise):** How well do raw single-engine OCR confidences predict field-level errors under Vietnamese administrative degradations (red stamp overlap, skew, low DPI)?
  - **H1:** Raw single-engine token confidence exhibits severe overconfidence (high ECE and high silent risk at >80% coverage) under red-stamp occlusion and Vietnamese diacritic noise.
  - *Disconfirmation criterion:* If single-engine raw confidence already achieves $<1\%$ silent error at $\ge 90\%$ coverage across all degradation strata.

- **RQ2 (Cross-Engine Consensus + Deterministic Invariants):** Does combining lightweight on-device multi-engine agreement (Apple Vision + Tesseract) with deterministic field invariants (CCCD structure, calendar validity, bounding-box alignment) significantly reduce AURC compared to single-engine confidence thresholding?
  - **H2:** Cross-engine disagreement + deterministic format/checksum constraints will reduce AURC and achieve significantly higher coverage at fixed target silent-error budgets ($\text{Risk} \le 0.5\%$ and $\le 1.0\%$) than either engine alone.
  - *Disconfirmation criterion:* If multi-engine consensus + invariants fails to outperform the best single engine on paired bootstrap AURC ($p > 0.05$) or causes excessive latency overhead without risk reduction.

- **RQ3 (Selective Local Escalation):** When abstained fields are routed to a bounded local VLM (e.g., on-device MLX VLM) vs. human review, what fraction of total manual verification effort can be saved without violating the silent-error budget?

---

## 2a. Scope after the real-handwriting audit (2026-11-25)

`audits/real_handwriting` ran the pilot's engines and verifiers on 1,838 real handwritten Vietnamese
addresses (Cinnamon AI set). The engines that worked on fonts fail on pen strokes:

- Apple Vision gets 83.7% of the parsed address values wrong (39.9% on handwriting fonts).
- Tesseract `vie` gets none right.
- Qwen3.5-4B, on a 200-line sample, matches an exact card on 23.5% of lines, against a bar of 50%
  set before the run.

Raw confidence stays at 1.0 throughout, so H1 holds on real data.

Decision, by the rule set before the Qwen run: the scope narrows to **printed and typed documents
plus the CCCD QR code**. Handwritten fields are reported as a measured limit, not a target. RQ3
(VLM escalation) stays open only for printed crops that the gate abstains on. The next unknown in
the narrowed scope is real scans with real seals (the stamp results in `audits/ocr_pilot` are upper
bounds).

Both follow-ups ran the same day, with thresholds written first:

- `audits/real_scans` (193 government documents). The number and issue date are filled in
  after signing, by hand on scans and as an overlay on signed PDFs, so even "printed" documents
  need handwritten digits read. Vision gets both right on 89.1% (bar 95%: ITERATE). Red dropout
  removes real seals and costs nothing measurable. The one engine error that passes every format
  check ("2223" read as "2023") is exactly what only an exact side A can catch.
- `audits/cccd_qr` (synthetic payloads only). 2,526 decodes, no silent error, Vietnamese intact:
  the QR code holds up as the exact side A, as an upper bound until real cards are tested with
  consent.

The number and date then went through two more pre-registered batches. Parser v2 failed on
unseen documents (upper bound 5.4%, KILL). v3, which also requires Qwen3.5-4B to agree with
Vision, passed on 340 unseen documents (264 accepted, upper bound 2.9% against a 3% bar), and
its three disagreements with the listing were all faults in the listing. Two-engine agreement
is therefore the working gate for printed headers; the open question is an exact side A, since
the publication listing is wrong about 1% of the time.

## 3. Evaluation Protocol

1. **Benchmark Construction (Privacy-Safe):**
   - Synthetic & template-generated Vietnamese administrative forms with exact ground-truth field annotations (zero real citizen PII in public splits).
   - Controlled perturbation suite: Clean, Skew ($\pm 3^\circ, \pm 7^\circ$), Red-Stamp Occlusion (varying opacity & overlap), Low-DPI Blur, and Combined Stress.
2. **Baselines vs. Proposed Method:**
   - `B0`: Tesseract `vie+eng` only (raw TSV confidence thresholding).
   - `B1`: Apple Vision only (raw observation confidence thresholding).
   - `M1`: Dual-engine consensus (Vision $\cap$ Tesseract token/character agreement) + deterministic field schema/checksum verifier.
   - `M2`: `M1` + selective local VLM escalation on abstained crops only.
3. **Metrics & Statistics:**
   - Risk–Coverage curves, AURC, Coverage@Risk$\le 0.5\%$, Field EM, CER, ECE, and median ms/page latency on Apple Silicon.
   - Paired bootstrap confidence intervals and Wilcoxon signed-rank tests across documents.
