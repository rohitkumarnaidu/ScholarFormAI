<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Troubleshooting Guide
description: Common issues, fixes, and debugging procedures
sidebar_position: 15
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Troubleshooting Guide

## Table of Contents
- [1. Upload Errors](#1-upload-errors)
- [2. Processing Issues](#2-processing-issues)
- [3. Generator / Synthesis Issues](#3-generator--synthesis-issues)
- [4. Preview Problems](#4-preview-problems)
- [5. Download Problems](#5-download-problems)
- [6. Auth / Security Errors](#6-auth--security-errors)
- [7. Billing Errors](#7-billing-errors)
- [8. XSS / Input Sanitization Notes](#8-xss--input-sanitization-notes)
- [9. Debug Commands](#9-debug-commands)
- [10. Escalation Checklist](#10-escalation-checklist)

## 1. Upload Errors

### Error: Invalid file type

Cause:
- Uploaded file is not `.docx`, `.pdf`, or `.tex`.

Fix:
- Convert your document to one of the supported formats.
- Re-upload using the **Upload** page.

### Error: File too large

Cause:
- File exceeds `50 MB`.

Fix:
- Compress images inside the manuscript.
- Split appendices into separate files.

---

## 2. Processing Issues

### Status does not move from RUNNING

Cause:
- Backend worker delay
- Temporary DB/network issue

Fix:
1. Refresh the page.
2. Check backend logs.
3. Re-run with the same file.

### Job failed during formatting

Cause:
- Malformed input document
- Template mismatch

Fix:
1. Try with `None` template once.
2. Re-run with target template.
3. Check `/api/v1/documents/{job_id}/status` for error details.

---

## 3. Generator / Synthesis Issues

### Agent session hangs on "Generating"

Cause:
- LLM provider unavailable or rate-limited
- Prompt too long

Fix:
1. Check LLM provider status (NVIDIA NIM > Groq > DeepSeek fallback chain).
2. Try a shorter prompt.
3. Restart the session.

### Synthesis SSE stream disconnects

Cause:
- Network timeout during document chunking/embedding

Fix:
1. Reduce the number of PDFs (max 6).
2. Ensure each PDF is under 50 MB.
3. Retry the session.

---

## 4. Preview Problems

### Preview empty or partial

Cause:
- Structured content missing
- API request failed

Fix:
- Retry preview page.
- Check network tab for `/api/v1/documents/{job_id}/preview`.
- Verify document reached `COMPLETED` status.

---

## 5. Download Problems

### Download button fails

Cause:
- Output not ready
- Temporary network/server error

Fix:
1. Confirm status is `COMPLETED`.
2. Retry download from **Download** page.
3. Try DOCX first, then PDF/JSON.

### PDF unavailable

Cause:
- PDF conversion dependency missing on backend host.

Fix:
- Ensure LibreOffice is available on server/runtime.

---

## 6. Auth / Security Errors

### 401 Unauthorized

Fix:
- Log out and log in again.
- Verify your Supabase access token is valid at `/api/v1/auth/me`.

### CSRF token mismatch

Cause:
- Stale cookies/session

Fix:
1. Clear site cookies.
2. Refresh app.
3. Retry request.

---

## 7. Billing Errors

### Stripe webhook fails

Cause:
- `STRIPE_WEBHOOK_SECRET` not set or mismatched.

Fix:
1. Verify `STRIPE_WEBHOOK_SECRET` in backend `.env`.
2. Run `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`.
3. Check Stripe dashboard for webhook delivery logs.

### Cannot access billing portal

Cause:
- User has no active Stripe customer ID.

Fix:
- Ensure at least one successful payment or subscription exists.

---

## 8. XSS / Input Sanitization Notes

Input fields are sanitized before API submission. If special characters are stripped:
- Avoid pasting raw HTML tags into normal text fields.
- Use plain text for title, name, and metadata fields.

---

## 9. Debug Commands

Frontend:
```bash
cd frontend
npm run test
npm run build
```

Backend:
```bash
cd backend
python -m pytest tests/test_template_renderer.py
python -m pytest tests/test_export_pipeline.py --no-cov
```

---

## 10. Escalation Checklist

When raising a bug, include:
- Input file type and size
- Template selected
- Exact error message
- Job ID or session ID
- Browser + OS
- Backend logs (if accessible)
