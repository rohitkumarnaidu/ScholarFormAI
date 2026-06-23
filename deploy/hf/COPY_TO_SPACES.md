<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Hugging Face Spaces Copy Map (12 URLs)

This project now uses 6 service pairs (primary + shadow = 12 Space URLs).

## 1) Existing service pairs (already live in your HF account)

- GROBID:
  - `https://rohith083-scholarform-grobid-primary.hf.space`
  - `https://rohith083-scholarform-grobid-shadow.hf.space`
  - Template: `deploy/hf/grobid-service/*`
- Docling:
  - `https://rohith083-scholarform-docling-primary.hf.space`
  - `https://rohith083-scholarform-docling-shadow.hf.space`
  - Template: `deploy/hf/docling-service/*`
- OCR:
  - `https://rohith083-scholarform-ocr-primary.hf.space`
  - `https://rohith083-scholarform-ocr-shadow.hf.space`
  - Template: `deploy/hf/ocr-service/*`
- DOCX Converter:
  - `https://rohith083-scholarform-docx-converter-primary.hf.space`
  - `https://rohith083-scholarform-docx-converter-shadow.hf.space`
  - Template: `deploy/hf/docx-converter-service/*`

## 2) New heavy model pairs (repo templates provided)

- Nougat:
  - `https://rohith083-scholarform-nougat-primary.hf.space`
  - `https://rohith083-scholarform-nougat-shadow.hf.space`
  - Copy files from `deploy/hf/nougat-service/*`
- SciBERT:
  - `https://rohith083-scholarform-scibert-primary.hf.space`
  - `https://rohith083-scholarform-scibert-shadow.hf.space`
  - Copy files from `deploy/hf/scibert-service/*`

## Health path expectations

- GROBID: `/api/isalive`
- All others: `/`

## Important backend note

- Keep Render backend `PRELOAD_AI_MODELS=false`.
- HF Spaces preload model weights at service startup (`app.py`) and backend calls them remotely.
