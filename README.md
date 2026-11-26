# `verified-document-intake`: Selective & Verified On-Device Document Digitization

Research and engineering repository for **deterministic PDF/OCR intake, field-level uncertainty calibration, and selective abstention** on privacy-sensitive, low-resource administrative documents (e.g., Vietnamese municipal/commune records) running entirely on-device.

---

## 0. Status: what does not work yet

Updated after every audit run. Bad numbers go here first. Last update: 2026-11-26.

| What | Measured | Bar (set before the run) | Verdict | Source |
|---|---|---|---|---|
| Real handwritten addresses, Apple Vision | 83.7% of parsed values wrong (1,838 lines) | — | Out of scope | `audits/real_handwriting` |
| Real handwritten addresses, Tesseract `vie` | 100% wrong | — | Out of scope | `audits/real_handwriting` |
| Real handwritten addresses, Qwen3.5-4B | 23.5% match an exact card (200 lines), 5.1 s per line | ≥ 50% | Missed | `audits/real_handwriting` |
| Raw engine confidence (H1) | Vision gives 1.0 to 99.3% of real lines, right or wrong | — | H1 holds | `audits/real_handwriting` |
| Number + date on real government documents, Vision | Batch 1: number 94.8%, date 93.8%, both 89.1% (193 docs). Batch 2: 89.1%, 92.7%, both 85.5%. Batch 3: 92.1%, 92.6%, both 87.6% (340 docs) | ≥ 95% each | ITERATE (three times) | `audits/real_scans` |
| Same, Tesseract `vie` | Both right on 38.3% | — | Not usable alone | `audits/real_scans` |
| Wrong values that pass the format checks | Batch 1: 7 of 179 (upper bound 7.2%). Batch 2: 13 of 178 (upper bound 11.4%). Batch 3: 25 of 323 (upper bound 10.6%) | — | Format checks are not enough | `audits/real_scans` |
| Stricter parser v2 on batch 2 | 4 wrong of 168 accepted, upper bound 5.4% (batch 1 post hoc: 1 of 168 did not replicate) | upper bound ≤ 3% GO, > 5% KILL | **KILL** | `audits/real_scans` |
| v3: year rule + Qwen must agree with Vision (third batch, 340 unseen docs) | 3 wrong of 264 accepted, upper bound **2.9%** (bar 3%, margin 0.1 points); coverage 77.6%; Qwen rejects 30 correct Vision reads | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO, narrowly | `audits/real_scans` |
| v4 (all of Vision's possible readings + Qwen + e-signature date), **in-sample** on 726 docs | 574 accepted (79.1%), 0 wrong against the page, 3 listing faults; batch 3 alone 72.6% coverage. Not yet tested on unseen documents | — | Needs a fourth batch | `audits/real_scans` |
| Two engines making the same error | "2223"→"2023" (Vision and full-resolution Qwen), "142"→"1H2", "ngày21" → day 2 (both): agreement is not independence | — | Known limit | `audits/real_scans` |
| The listing as ground truth | All 3 v3 "errors" are listing faults (wrong PDF, a date that differs from the page, a Cyrillic letter): 3 of 264 accepted (1.1%). Found after scoring | — | Side A is not exact | `audits/real_scans` |
| Red dropout, cost on page 1 | Batch 1: 0 points. Batch 2: −1.6. Batch 3: −1.4 | ≤ 1 GO, > 2 KILL | Between bars | `audits/real_scans` |
| PDF text layer for number and date | Blank in 62% of signed PDFs (filled in after signing); batch 3: blank in 69%, and 1 wrong (the parser cut "VPCP-V.I") | — | OCR still needed | `audits/real_scans` |
| Certified risk ≤ 1% | Not reached anywhere on real data. v3 on batch 3: 264 accepted, 3 wrong, p = 0.73 (0 wrong against the page would give p = 0.07, but that is post hoc) | α = 1%, δ = 0.1 | Not certified | all |
| CCCD QR silent errors | 0 of 2,526 decodes, but **synthetic codes only**; decode rate 69.8% under blur | 0 errors | GO (upper bound) | `audits/cccd_qr` |

Untested: real CCCD cards, phone photos of real documents, commune-level paperwork, the signer's
name under a seal.

---

## 1. Problem Formulation

Given a document page $D$ (digital PDF, scanned raster, or photograph) containing a set of target fields $F = \{f_1, \dots, f_k\}$ (e.g., citizen ID numbers, dates, names, structured clauses), an intake system produces for each field $f_i$:
$$(\hat{v}_i, \hat{c}_i, a_i) \in \mathcal{V}_i \times [0, 1] \times \{\text{ACCEPT}, \text{ABSTAIN}\}$$
where $\hat{v}_i$ is the extracted value, $\hat{c}_i$ is a calibrated confidence score derived from multi-engine OCR agreement and deterministic structural invariants, and $a_i$ decides whether to auto-commit or escalate to human review / heavier local VLM verification.

In administrative digitization, **silent errors on identity fields are unacceptable**, whereas escalating 100% of fields eliminates automation value. We study the trade-off using:

1. **Risk–Coverage Curve & AURC:** Selective error rate on accepted fields ($\text{Risk} = \mathbb{P}(\hat{v}_i \ne v_i^* \mid a_i = \text{ACCEPT})$) as a function of automation coverage ($\text{Coverage} = \mathbb{P}(a_i = \text{ACCEPT})$).
2. **Field Exact Match (EM) & Character Error Rate (CER):** Stratified across clean scans vs. realistic degradation regimes (red ink stamp occlusion, skew, low DPI, mixed handwriting).
3. **Expected Calibration Error (ECE):** Reliability of raw OCR token confidences vs. cross-engine consensus + deterministic schema/checksum verification.

---

## 2. Design Principles

- **Zero hidden imports:** Importing `document_intake` loads no OCR engine, PyQt, LLM, or application code. Optional engines (`pypdf`, Apple Vision via PyObjC, Tesseract) are loaded strictly on demand.
- **Explicit failure semantics:** Digital PDF reading never silently invokes OCR; encrypted/corrupt/missing PDFs raise typed `PDFReadError` with stable error codes.
- **Strict privacy boundary:** All inference and verification run 100% offline/on-device. Real citizen PII must never be committed to version control.

---

## 3. Repository Structure

```text
verified-document-intake/
├── audits/                 # Pre-registered experiments: code + aggregate results (data stays in data/private/)
├── docs/
│   ├── RESEARCH_PLAN.md    # Hypotheses, degradation regimes, Risk–Coverage protocol
│   └── GUIDE.md            # Integration guide (RAT & digitization clients), privacy rules
├── src/
│   └── document_intake/
│       ├── pdf.py          # Digital PDF reader + macOS PDFKit native OCR fallback
│       ├── tesseract.py    # Tesseract vie+eng TSV token/bbox/confidence runner
│       ├── vision.py       # Apple Vision OCR tokens with top-left pixel bboxes
│       ├── ocr_paragraphs.py  # Conservative geometry-based OCR soft-wrap joining
│       └── pdf_text.py     # Ligature/hyphenation cleanup for copied PDF text
├── tests/                  # Deterministic intake, robustness, and layout contract tests
├── pyproject.toml          # uv-managed Python 3.11+ package (`document_intake`)
└── LICENSE                 # MIT License
```

---

## 4. Quickstart

```bash
# Install package + dev tools via uv
uv sync

# Run unit and robustness contract tests
uv run pytest

# Lint codebase
uv run ruff check src tests
```

As a dependency in downstream applications (e.g., RAT or a local administrative digitization client):

```toml
dependencies = [
    "verified-document-intake[pdf] @ git+https://github.com/Thundercok/verified-document-intake.git",
]
```
