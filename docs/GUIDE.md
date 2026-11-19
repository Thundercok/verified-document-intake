# Developer, Integration & Privacy Guide

## 1. Environment Setup

```bash
uv sync
uv run ruff check src tests
uv run pytest
```

External prerequisites for live OCR runs:
- **macOS Apple Vision:** requires macOS with `pyobjc-framework-Cocoa` (`uv sync --extra vision`).
- **Tesseract OCR:** requires `tesseract` binary on `PATH` with `vie` + `eng` traineddata.

---

## 2. Core Contracts (Do Not Break Downstream Clients)

`document_intake` is consumed directly by `selective-delegation-agent` (RAT) and external digitization clients:

1. **Lazy Engine Loading:** Importing `document_intake.pdf`, `document_intake.tesseract`, or `document_intake.vision` MUST NOT import `pypdf`, `PIL`, `objc`, `PyQt6`, or `rat`.
2. **Digital vs. Scanned Separation:** `read_pdf(...)` reads digital text streams only and never silently triggers OCR. Scanned fallback is explicit (`read_pdf_native`).
3. **Stable Error Codes:** Expected PDF failures raise `PDFReadError(ValueError)` with `.code` in:
   - `file_not_found`
   - `file_unreadable`
   - `invalid_pdf`
   - `encrypted_pdf`
   - `pdf_engine_unavailable`
4. **Finite Budgets:** Respect `max_pages`, `max_chars`, and subprocess `timeout` strictly; never hang or retry timed-out OCR binaries silently.

---

## 3. Data Privacy Rule (Strict)

- **NEVER commit real citizen records, CCCD numbers, birth certificates, or unredacted scans** to Git.
- Keep any private test scans strictly inside `data/private/` (gitignored) and use synthetic / anonymized templates for all public benchmarks and CI fixtures.
