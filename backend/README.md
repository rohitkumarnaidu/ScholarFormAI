<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Automated Academic Manuscript Formatter (Backend)

## Overview
The system combines deterministic document processing with optional OCR and AI enrichment.
OCR ensures accessibility for scanned inputs, while AI provides advisory insights without compromising reproducibility or control.

## Key Features
- Multi-format input support (DOCX, PDF, MD, HTML, TXT, ODT, RTF)
- **3-Tier PDF Parsing Fallback**: 
  1. GROBID (best metadata, requires 1.5GB RAM via Docker)
  2. Docling (Python-native, ~150MB RAM, IBM models)
  3. PyMuPDF (fast basic text parsing)
- **AI Enrichment**: Optional advisory hints for section detection and readablity using NVIDIA NIM.
- Deterministic document understanding (no AI / LLMs involved in core logic).
- Template-aware formatting (17 templates: acm, apa, chicago, elsevier, harvard, ieee, mla, modern_blue, modern_gold, modern_red, nature, none, numeric, portfolio, resume, springer, vancouver).
- Backend runs exclusively on **FastAPI** (Python 3.12 required).

## Architecture
Input Conversion (OCR) → Parsing → Normalization → Structure Detection →
AI Enrichment → Classification → Figures → References → Validation → Formatting → Export

*(Note: There is no Spring Boot gateway. The backend is a pure Python modular monolith.)*

## Supported Input Formats
| Format | Handling |
|------|---------|
| DOCX | Native |
| PDF | GROBID / Docling / LibreOffice / Tesseract OCR (if scanned) |
| MD / HTML / TXT | Pandoc |
| ODT / RTF | LibreOffice |

## API Usage
### POST /api/v1/documents/upload

**Request**:
- `file`: manuscript (any supported format)
- `template_name` (optional): `ieee` | `springer` | `acm` | `apa` | `chicago` | `elsevier` | `harvard` | `mla` | `modern_blue` | `modern_gold` | `modern_red` | `nature` | `none` | `numeric` | `portfolio` | `resume` | `vancouver`
- `enable_ocr` (boolean, default: True): Auto-detect scanned PDFs
- `enable_ai` (boolean, default: False): Enable advisory analysis flags

**Response**:
- `validation_result` (JSON dict)
- `message` (string)
- `output_path` / `download_url` (if generated)
- `ocr_used` (boolean)
- `ai_enabled` (boolean)

## Validation Rules
- **Missing References** → ERROR
- **Missing Abstract / Introduction** → WARNING
- **Figure referenced but missing** → WARNING
- **Uncaptioned figures** → WARNING
- **Missing reference authors** → ERROR

## Running Locally
**Prerequisites**: Python 3.12

**Command**:
```bash
uvicorn app.main:app --reload --port 8000
```

## Testing
Manual script fixtures were removed during repository cleanup. Use the automated test
suite as the source of truth.

Run the `trusted-core` test profile for quick safety checks:
```bash
pytest tests -m "not integration and not llm" -x -q
```

## Limitations
- PDF layout may degrade during conversion if GROBID is disabled and file is complex.
- Equations are treated as plain text.
- No citation renumbering across styles yet.
