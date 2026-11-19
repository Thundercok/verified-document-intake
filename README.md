# `verified-document-intake`: Selective & Verified On-Device Document Digitization

Research and engineering repository for **deterministic PDF/OCR intake, field-level uncertainty calibration, and selective abstention** on privacy-sensitive, low-resource administrative documents (e.g., Vietnamese municipal/commune records) running entirely on-device.

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
