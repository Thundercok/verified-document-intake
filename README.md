# `verified-document-intake`: Selective & Verified On-Device Document Digitization

Research and engineering repository for **deterministic PDF/OCR intake, field-level uncertainty calibration, and selective abstention** on privacy-sensitive, low-resource administrative documents (e.g., Vietnamese municipal/commune records) running entirely on-device.

---

## Contents

- [Status: what does not work yet](#0-status-what-does-not-work-yet)
- [Problem Formulation](#1-problem-formulation)
- [Design Principles](#2-design-principles)
- [Repository Structure](#3-repository-structure)
- [Quickstart](#4-quickstart)

---

## 0. Status: what does not work yet

Updated after every audit run. Bad numbers go here first. Last update: 2026-11-28.

| What | Measured | Bar (set before the run) | Verdict | Source |
|---|---|---|---|---|
| Real handwritten addresses, Apple Vision | 83.7% of parsed values wrong (1,838 lines) | — | Out of scope | `audits/real_handwriting` |
| Real handwritten addresses, Tesseract `vie` | 100% wrong | — | Out of scope | `audits/real_handwriting` |
| Real handwritten addresses, Qwen3.5-4B | 23.5% match an exact card (200 lines), 5.1 s per line | ≥ 50% | Missed | `audits/real_handwriting` |
| Raw engine confidence (H1) | Vision gives 1.0 to 99.3% of real lines, right or wrong | — | H1 holds | `audits/real_handwriting` |
| Number + date on real government documents, Vision | Batch 1: number 94.8%, date 93.8%, both 89.1% (193 docs). Batch 2: 89.1%, 92.7%, both 85.5%. Batch 3: 92.1%, 92.6%, both 87.6% (340 docs). Batch 4: 91.8%, 90.0%, both 84.4% (500 docs; scans 81.1%). Batch 5: **77.0%, 77.8%**, both 72.2% (500 docs; scans 87.9%, 89.0%; 81 consolidated texts have no number on page 1). Batch 6: **73.6%, 75.0%**, both 70.8% (500 docs; scans 91.2%, 92.8%; 107 consolidated texts). Batch 7: 90.2%, **84.2%**, both 77.6% (500 docs, 436 scans, only 10 consolidated texts). Batch 8: **81.0%, 82.8%**, both 71.2% (500 docs, 455 scans; 44 laws, 54 Standing Committee resolutions, 20 consolidated texts). Batch 9: **82.0%, 84.0%**, both 73.4% (500 docs, 417 scans; 28 consolidated texts, 30 laws and resolutions). Batch 10: 83.2%, **75.2%**, both **68.6%** (500 docs, 371 scans, both right on 66.6% of scans; 42 laws and resolutions, 10 consolidated texts; older documents, Oct–Dec 2024) | ≥ 95% each | RETHINK on batch 10; ITERATE on batches 7 and 8 (RETHINK on 5 and 6, ITERATE four times before) | `audits/real_scans` |
| Same, Tesseract `vie` | Both right on 38.3% | — | Not usable alone | `audits/real_scans` |
| Wrong values that pass the format checks | Batch 1: 7 of 179 (upper bound 7.2%). Batch 2: 13 of 178 (upper bound 11.4%). Batch 3: 25 of 323 (upper bound 10.6%). Batch 4: 15 of 423 (upper bound 5.4%). Batch 5: **78 of 439 (upper bound 21.0%)**. Batch 6: **116 of 470 (upper bound 28.2%)**. Batch 7: 39 of 427 (upper bound 11.8%). Batch 8: **53 of 409 (upper bound 16.0%)**. Batch 9: **61 of 428 (upper bound 17.3%)**. Batch 10: **41 of 384 (upper bound 13.6%)**. Mostly title dates in consolidated texts | — | Format checks are not enough | `audits/real_scans` |
| Stricter parser v2 on batch 2 | 4 wrong of 168 accepted, upper bound 5.4% (batch 1 post hoc: 1 of 168 did not replicate) | upper bound ≤ 3% GO, > 5% KILL | **KILL** | `audits/real_scans` |
| v3: year rule + Qwen must agree with Vision (third batch, 340 unseen docs) | 3 wrong of 264 accepted, upper bound **2.9%** (bar 3%, margin 0.1 points); coverage 77.6%; Qwen rejects 30 correct Vision reads | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO, narrowly | `audits/real_scans` |
| v4 (all of Vision's possible readings + Qwen + e-signature date), fourth batch, 500 unseen docs, truth = page (blind adjudication) | 395 accepted (79.0%), **1 wrong**, upper bound 1.2%. The error: "QĐ" output as "QD" (Vision dropped the stroke, the Đ/D tolerance let it agree with Qwen). Scans only 72.4% accepted (PDFs 91.0%). Adjudicator = the agent that built v4, not an independent person | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO | `audits/real_scans` |
| v5 (v4 + keep Đ by code list), fifth batch, 500 unseen docs, no person involved | 328 accepted (**65.6%, coverage bar missed**), 0 wrong, upper bound 0.9%. v5 = v4 on all 500: the Đ rule never fired, so it is still untested out of sample. 81 consolidated texts (VBHN) have no number on page 1; v5 abstains on all. Without them 78.3% (post hoc, does not count). Text-layer PDFs 45.1% accepted | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO on risk, **coverage missed** | `audits/real_scans` |
| v6 (v5 + VBHN number without year + number read from the VBHN authentication block), sixth batch, 500 unseen docs, no person involved | 355 accepted (**71.0%: bar met by 1 point**; 95% interval 66.9–74.8%, so the next batch can miss), 0 wrong, upper bound 0.8%. All 31 extra accepts come from the block; the year rule added none. **Consolidated texts: 31 of 107 accepted (29.0%)**; block not found in 59 text-layer VBHN (21 of them hold the phrase in another layout, seen post hoc), 9 VBHN are scans with no path. Text-layer PDFs 46.5%. Reader = the agent that built v6 | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO, coverage narrowly | `audits/real_scans` |
| v7 (v6 + looser authentication-block locator), seventh batch, 500 unseen docs, no person involved | 350 accepted (**70.0%: exactly at the bar**; 95% interval 65.8–74.0%), **2 wrong**, upper bound 1.8%; **certificate fails** (p = 0.319). Both errors are handwritten page-1 numbers that Vision and Qwen misread the same way; v5 and v6 make them too. **Only 10 VBHN in the batch** (block found in 5, 4 accepted), so the v7 change (+2 accepts) is barely tested. 436 of 500 are scans, 67.7% accepted. Reader = the agent that built v7 | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO on risk bar, coverage at the bar, **not certified** | `audits/real_scans` |
| v8 (v7 + abstain when two number candidates pass + register-order check within the batch), eighth batch, 500 unseen docs, no person involved | 313 accepted (**62.6%: coverage bar missed by 7.4 points**; 95% interval 58.2–66.9%), 0 wrong, upper bound 1.0%, certified (p = 0.043). **v7 on the same batch: 318, 0 wrong**: the two new rules caught 0 errors and cost 5 correct accepts. Rule A never fired. **Rule B dropped 5 correct provincial decisions** ("48–53/2025/QĐ-UBND" from different provinces, grouped as one register by their shared tail): a design fault. Post hoc: 44 laws (0 accepted), 54 NQ-UBTVQH15 (7; Vision reads "15" as "1S"/"IS"), 20 VBHN (1). Scans 60.0% accepted. Reader = the agent that built v8 | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO on risk, certified, **coverage missed** | `audits/real_scans` |
| v9 (v8 + date from the law's closing sentence on the last page + look-alike tail merge + rule B scoped away from local and "QH" tails), ninth batch, 500 unseen docs, no person involved | 362 accepted (72.4%, bar met; 95% interval 68.3–76.3%), **1 wrong**, upper bound 1.3%; **certificate fails** (p = 0.122; one error needs ≥ 388 accepts). The error: handwritten "02/2025/TT-BTTTT" read as "62" by both engines; rule B cannot catch it (its neighbour "01" carries the same date); v5–v8 make it too. **v8 on the same batch: 327 (65.4%, would have missed)**. Post hoc: 35 gains, 0 wrong (closing sentence 21, block 19); 0 losses. Laws and resolutions 20 of 30, VBHN 19 of 28. Scans 70.5%. Reader = the agent that built v9 | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO on risk, coverage met, **not certified** | `audits/real_scans` |
| v10 (v9 + a third reader: Gemma 4 E4B reads a crop of the number line; page-1 and last-page accepts kept only if its leading number agrees), tenth batch, 500 unseen docs, no person involved | 324 accepted (**64.8%: coverage bar missed by 5.2 points**; 95% interval 60.5–68.9%), 0 wrong, upper bound 0.9%, certified (p = 0.039). **v9 on the same batch: 326 (65.2%), also missed**: the miss was pre-registered as a risk and is v9's, not the new rule's. **Rule G removed 2 correct accepts and caught 0 errors: the batch had no shared handwritten misread, so the third reader is still untested out of sample.** In-sample Gemma makes one of the three known misreads ("2615" → 2645). Post hoc: laws and resolutions 13 of 42, VBHN 4 of 10, everything else 68.5%; scans 60.1%. Gemma takes 6–9 s per crop and 9.7 GB on a 16 GB machine. Reader = the agent that built v10 | upper bound ≤ 3% GO, > 5% KILL; coverage ≥ 70% | GO on risk, certified, **coverage missed** | `audits/real_scans` |
| Two engines making the same error | "2223"→"2023" (Vision and full-resolution Qwen), "142"→"1H2", "ngày21" → day 2 (both); batch 4: "QĐ" → "QD" let through by the Đ/D tolerance; **batch 7: handwritten "2615" → 2645 and "2491" → 249, both engines, both accepted**; **batch 9: handwritten "02" → "62" (TT-BTTTT), both engines, accepted**: agreement is not independence. A third model family does not fully fix it: **in-sample, Gemma 4 reads "2615" as 2645 too**; batch 10 had no shared misread to test it on | — | **Still the main risk** (2 accepted errors in batch 7, 0 in batch 8, 1 in batch 9, 0 in batch 10; v8's register check could not catch the batch-9 one) | `audits/real_scans` |
| The listing as ground truth | All 3 v3 "errors" are listing faults (wrong PDF, a date that differs from the page, a Cyrillic letter): 3 of 264 accepted (1.1%). Found after scoring. Batch 4: 1 more (listing 21/08, page 11/08) among 409 report-only accepts; 2 of 100 spot-checked entries carry a Cyrillic "Р". Batch 5: 1 of 328 accepts (listing "QD-UBND", page "QĐ-UBND"). Batch 6: 0 of 355. Batch 7: 2 of 350 ("UBTVVQH15" for "UBTVQH15"; "01/VBHN" where the page prints "1"). Batch 8: 1 of 313 (listing "TT-BNNMT", page "TT-BTNMT"). Batch 9: 2 of 362 (listing "VPCP-VN", page "VPCP-CN"; listing 31/12, page 30/12). Batch 10: 0 of 324 | — | Side A is not exact | `audits/real_scans` |
| Red dropout, cost on page 1 | Batch 1: 0 points. Batch 2: −1.6. Batch 3: −1.4. Batch 4: +0.4. Batch 5: −0.4. Batch 6: −0.6. Batch 7: 0. Batch 8: −0.4. Batch 9: 0. Batch 10: +1.2 | ≤ 1 GO, > 2 KILL | Mixed: GO on 8 of 10 batches | `audits/real_scans` |
| PDF text layer for number and date | Blank in 62% of signed PDFs (filled in after signing); batch 3: blank in 69%, and 1 wrong (the parser cut "VPCP-V.I"); batch 4: no number and date in 57%, 2 wrong; batch 5: both found in only 6.9% (0 wrong); batch 6: 0.8%; batch 7: 18.8% of 64 text-layer PDFs (0 wrong); batch 8: 24.4% of 45 (1 wrong); batch 9: 4.8% of 83 (0 wrong); batch 10: 13.2% of 129 (0 wrong) | — | OCR still needed | `audits/real_scans` |
| Public dataset VBCP-NumDate (tier 1, `dataset/`) | 3,226 documents, metadata and OCR text only. Labels = portal listing for 3,215 (11 adjudicated); page bodies **not screened for personal data**, so no images released; licence of the source (Luật SHTT Art. 15) **not legally verified** | — | Tier 1 built locally, not published | `dataset/README.md` |
| Certified risk ≤ 1% | v4 on batch 4 (pre-registered): 395 accepted, 1 wrong, p = 0.094, **narrowly** (one error needs ≥ 388 accepted). Only central-government documents on vanban.chinhphu.vn, 06–08/2026; truth from the listing plus 2 adjudicated pages. Blind spot check (pre-registered): 100 random agreeing docs read from the page, 0 hidden errors, which cannot rule out up to 3.0% hidden. Same agent as reader. v5 on batch 5 (pre-registered, no person involved): 328 accepted, 0 wrong, p = 0.037; spot check 0 of 100 hidden (up to 3.0% possible); 6 of 500 are provincial. v6 on batch 6 (pre-registered, no person involved): 355 accepted, 0 wrong, p = 0.028; spot check 0 of 100 hidden (up to 3.0% possible). **v7 on batch 7 (pre-registered, no person involved): 350 accepted, 2 wrong, p = 0.319, not certified**; with 2 errors certification needs ≥ 531 accepts, so no batch of 500 can pass. v8 on batch 8 (pre-registered, no person involved): 313 accepted, 0 wrong, p = 0.043, certified, but coverage 62.6%; spot check 0 of 101 hidden (up to 2.9% possible). **v9 on batch 9 (pre-registered, no person involved): 362 accepted, 1 wrong, p = 0.122, not certified** (one error needs ≥ 388 accepts); spot check 0 of 140 hidden, every last-page and block accept read (up to 3.0% possible among page-1 accepts). v10 on batch 10 (pre-registered, no person involved): 324 accepted, 0 wrong, p = 0.039, certified, but coverage 64.8%; spot check 0 of 129 hidden, every last-page and block accept read (up to 3.0% possible among page-1 accepts). Not commune paperwork, not phone photos, not CCCD | α = 1%, δ = 0.1 | Certified on 5 of 7 batches tested; **failed on batches 7 and 9** | `audits/real_scans` |
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
├── dataset/                # VBCP-NumDate public release, tier 1: metadata, OCR text, download + build scripts
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
