<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — User Guide
description: End-to-end workflows for formatter, AI generator, and synthesis
sidebar_position: 10
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI User Guide

## 1. Overview

ScholarForm AI helps you upload an academic manuscript, apply a journal template, validate structure, and export final output. It also includes an **AI Generator** for creating manuscripts from scratch and a **Synthesis** engine for combining multiple source documents.

### Supported Formats

**Upload (input):** `.docx`, `.pdf`, `.tex`
**Export (output):** `DOCX`, `PDF`, `LaTeX`, `JSON`
**Synthesis input:** 2–6 `.pdf` files

Maximum file size: `50 MB`.

---

## 2. End-to-End Workflow (Formatter)

1. Open the app and go to **Upload**.
2. Upload a valid manuscript (`.docx`, `.pdf`, `.tex`).
3. Select a template (e.g. `IEEE`, `APA`, or `None`).
4. Set processing options (page numbers, cover page, TOC, page size).
5. Click **Process Document**.
6. Wait for the job to complete.
7. Review in:
   - **Compare Results** — before/after diff view
   - **Preview Document** — rendered HTML preview
8. Open **Download** and export in the required format.

---

## 3. AI Generator Workflow

1. Navigate to **Generate**.
2. Choose session type: **Multi-Doc Synthesis** or **AI Agent**.
3. For Synthesis: upload 2–6 PDF source documents.
4. For Agent: provide a prompt or topic.
5. Review the generated outline.
6. Approve the outline to begin section-by-section generation.
7. Follow progress via live SSE stream.
8. Download the completed DOCX.

---

## 4. Synthesis Engine

Combine multiple source PDFs into a single coherent manuscript:

1. Upload 2–6 PDF files.
2. Documents are chunked, embedded, and stored in a per-session ChromaDB vector store.
3. The pipeline extracts key sections from each source.
4. Review and approve the synthesized output.
5. Export as DOCX.

---

## 5. Export Options

Available export formats:

- **DOCX** — Editable Word document
- **PDF** — Print-ready PDF (requires LibreOffice on server)
- **LaTeX** — `.tex` file for Overleaf/TeX editors
- **JSON** — Structured data for programmatic use

Use the export dialog in the **Download** page to choose output format.

---

## 6. Security Features

- Client-side file type validation (`.docx`, `.pdf`, `.tex` only)
- User input sanitization before API submit
- CSRF token header support (`X-CSRF-Token`) with cookie/session fallback
- Virus scanning via ClamAV on uploaded files
- Row-Level Security (RLS) on Supabase Storage buckets

---

## 7. Common User Errors

- **Invalid file type:** Upload only `.docx`, `.pdf`, `.tex`.
- **File too large:** Keep file size under `50 MB`.
- **Download failed:** Retry after processing is complete; check network connection.
- **Synthesis fails:** Ensure all PDFs are readable and under 50 MB each.

---

## 8. Quick Checklist for New Users

- Use one of the supported file formats.
- Wait for status to become `COMPLETED`.
- Use **Preview** before final export.
- Export in the format required by the target journal.
- For AI generation, review and approve the outline before section writing begins.
