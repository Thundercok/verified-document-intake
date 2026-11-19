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
