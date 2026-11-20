# Related Work & Positioning (survey snapshot: 2026-11-20)

All numbers below are as reported by the authors (mostly preprints, mostly self-reported). Re-verify before citing.

## 1. Closest competitors: selective / risk-controlled document extraction

| Paper | Setup | Signals | Guarantee | Data | Gaps vs. us |
|---|---|---|---|---|---|
| **Perception, Layout, Validation** (OCBC, arXiv 2609.20110, Sep 2026) | VLM KIE → per-field p(correct) → auto-approve gate | 11 perception + 15 layout (retrieval NIW prior) + 8 validator features (IBAN mod-97, ISIN, dates, net+tax=gross), 2nd-VLM agreement; LightGBM | Learn-Then-Test, risk ≤ α w.p. 1−δ | DocILE, FATURA, VRDU (printed, English business docs) | No handwriting, no low-resource language, hosted VLMs. **States validators added little because their docs have few checkable identifiers.** |
| **ExtractConf** (Perfios, arXiv 2606.24420, IJCAI-ECAI'26 workshop) | GPT-4o KIE, automate vs. defer | Logprobs, Textract OCR conf, dual-call agreement, spatial; CatBoost + isotonic | None (empirical) | DocILE, CORD (English) | English only, cloud only, single OCR engine. AURC 0.145 → 0.043. |
| **VerifyDoc** (Zasti AI, arXiv 2608.14639, Jul 2026) | Per-field selective risk ≤ α | Verbalized, self-consistency, grounding, NLI, ambiguity-penalized support | Validity ladder: add-one → Mondrian LTT (Clopper-Pearson, cluster-corrected) → doc-level PAC | CORD, FUNSD, XFUND-de; **text-layer only, no vision** | Shows document clustering (design effect 1.8–2.5) breaks naive per-field bounds; **PAC tiers collapse to ≤0.5% coverage when signals are weak**. No validators, no handwriting. |
| **Geometric Risk Control** (NJUPT, arXiv 2603.19790, v4 Jul 2026) | Frozen VLM OCR, release or abstain | K=5 geometric views, consensus + edit dispersion + length screen | Empirical, protocol-fixed | IIIT5K, ICDAR13 (scene-text word crops) | Word crops only, no fields, no documents, no handwriting. |

**Bottom line:** "multi-signal confidence + conformal gate on KIE" is already published three times in 2026. The repo's original M1 (Vision ∩ Tesseract consensus + schema checks + risk–coverage) would be an incremental 4th entry. Do **not** pitch the gate itself as the contribution.

## 2. Raw OCR / document-parsing SOTA (we will not beat these, we should *use* them)

- OmniDocBench v1.6 leaders are ~1B dedicated doc models: TeleOCR, OvisOCR2, PaddleOCR-VL-1.6, MinerU2.5-Pro, GLM-OCR (~94–97). They beat Qwen3-VL-235B (~90).
- olmOCR-Bench: Chandra OCR 2 / LightOnOCR-3 (~86); DeepSeek-OCR ~76.
- Implication: Tesseract `vie` and Apple Vision are **baselines**, not the engines the paper should rest on. A ~1B OCR-VLM is small enough to consider on Apple Silicon (MLX/Core ML feasibility still to be checked per model).

## 3. Vietnamese-specific landscape

- Survey: *A Survey on Vietnamese Document Analysis and Recognition* (arXiv 2506.05061) lists the lack of large-scale Vietnamese document data as a key limitation.
- Handwriting datasets: UIT-HWDB (line/word), HANDS-VNOnDB (ICFHR 2018 online HW), Cinnamon address HW challenge, 5CD-AI Viet-Handwriting-OCR (~23k images).
- VLMs: Vintern-1B/3B (5CD-AI; Viet-OCR-VQA 137k images, receipts from MC-OCR 2021). A 2025 work reports VLM HTR CER ≈4.2% on VNOnDB-Line (unverified).
- Community benchmark: GLM-OCR / TeleOCR / PaddleOCR-VL-1.6 fine-tuned on UIT-HWDB (github.com/khanhlinh-innomation/vlm-handwriting-ocr).
- **Not found:** any Vietnamese administrative-form KIE benchmark, any civil-registry (hộ tịch) digitization paper, any work on calibration/abstention for Vietnamese OCR.

## 4. Handwritten-form extraction (any language)

- *From Handwriting to Structured Data* (arXiv 2604.16504): 17 MLLMs on a real mixed printed/handwritten medical form; field accuracy, CER, hallucination rate.
- *From Pixels to Structure* (arXiv 2610.11818): 8 lightweight VLMs on schema-guided JSON over handwritten/printed forms; general instruction-tuned VLMs beat OCR-specialized ones on structured output; handwriting adaptation left as future work.
- Neither does selective risk control.

## 5. Open gaps nobody covers (intersection is empty)

1. **Handwritten fields** under selective risk control.
2. **Vietnamese** (diacritic/tone-mark errors, syllable structure) under calibration.
3. **Strong deterministic verifiers.** 2609.20110 found validators weak *because their documents lacked them*. Vietnamese administrative documents are full of them:
   - CCCD 12 digits encode province code + century/gender digit + 2-digit birth year → **cross-field check against DOB and gender fields**.
   - Dates and money written twice, as digits and "bằng chữ" (in words) → **intra-document redundancy = free verifier**.
   - Administrative units must exist in a **versioned gazetteer** (pre/post 1-Jul-2025 merger to 34 provinces, district level removed) → old records vs. new records.
   - Closed set of valid Vietnamese syllables; name lexicons.
4. **On-device** cascade on Apple Silicon with measured latency.
5. **Human effort** (reviewer seconds), not just coverage.

## 6. Candidate thesis

> *Hard verifiers make certification non-vacuous.* VerifyDoc shows rigorous (cluster-corrected) per-field certificates collapse to near-zero coverage when confidence signals are weak, which is exactly the handwriting regime. We hypothesize that structural invariants and intra-document redundancy specific to Vietnamese administrative documents turn those vacuous certificates into useful coverage, on-device, at a fixed silent-error budget.

Contributions this implies:
1. **ViAdminForms** benchmark: mixed printed/handwritten Vietnamese administrative forms, field-level labels, document-grouped splits, degradation strata (stamp, skew, DPI, handwriting).
2. **Verifier library**: cross-field CCCD↔DOB↔gender, digits↔words, versioned gazetteer, syllable validity; each verifier reported with its own precision/recall as an error detector.
3. **Certified gate** built on cluster-corrected Mondrian LTT (VerifyDoc tier 3), with an ablation: signals only vs. signals + verifiers.
4. **On-device cascade** (Apple Vision → ~1B OCR-VLM → human) evaluated in reviewer-seconds per document.

Falsifier: if verifiers fire on too few fields (low coverage of the verifier set), coverage at α=1% will not move, and the thesis fails. Measure verifier field coverage on real form templates **before** building anything else.

**Audit outcome (2026-11-20): NO-GO for the single-form version.** Over 8 public templates, only 16.5–23.3% of critical fields have a usable verifier. Coverage is high only on financial documents (invoice 69%, NSNN 56%). Names, dates and addresses on civil and identity forms are the bottleneck. See [audits/verifier_coverage/README.md](../audits/verifier_coverage/README.md). The surviving direction is dossier-level cross-document redundancy (printed anchor documents verifying handwritten forms).

**Direction A outcome (2026-11-20): conditional GO.** Adding the documents that legally or customarily travel with each form raises critical-field coverage to 47.6% for archived dossiers with customary copies, and to 64.1% for counter intake that photographs the presented card. The forms alone reach 23.3%; with only the legally required dossier parts, coverage is 37.9% (borderline NO-GO). Names, addresses and IDs are fixed. Dates remain the gap, mostly signing dates. Revised thesis: *cross-document redundancy in administrative dossiers makes certified selective extraction of handwritten Vietnamese forms non-vacuous*. The core problems are then entity linking across documents and normalised comparison, including addresses across the 2025 merger. Details in [audits/verifier_coverage/README.md](../audits/verifier_coverage/README.md).

## Sources

- https://arxiv.org/abs/2609.20110
- https://arxiv.org/abs/2606.24420
- https://arxiv.org/abs/2608.14639
- https://arxiv.org/abs/2603.19790
- https://arxiv.org/abs/2412.07626 (OmniDocBench)
- https://roboflow.com/blog/best-open-source-ocr-models
- https://www.docsumo.com/blog/best-ocr-models
- https://arxiv.org/abs/2506.05061
- https://arxiv.org/abs/2408.12480 (Vintern-1B)
- https://huggingface.co/datasets/5CD-AI/Viet-Handwriting-OCR
- https://github.com/khanhlinh-innomation/vlm-handwriting-ocr
- https://arxiv.org/abs/2604.16504
- https://arxiv.org/abs/2610.11818
