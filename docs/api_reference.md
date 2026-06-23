<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Legacy API Reference (Deprecated)
description: Legacy API reference — superseded by API.md
sidebar_position: 80
version: "1.0"
status: ⚠️ Deprecated
owner: Docs Team
review_cadence: annually
last_updated: June 2026
---

# ⚠️ DEPRECATED — ScholarForm AI Legacy API Reference

> **DEPRECATED:** This file describes legacy API routes (without `/v1/` prefix) that are no longer the canonical API.  
> **Use Instead:** [`docs/API.md`](API.md) — the current v1 API reference with runtime-verified endpoints.  
> **Reason for deprecation:** All routes have migrated to `/api/v1/` with envelope response format. Legacy routes still work but carry `Deprecation` headers.

---

# ScholarForm AI - API Reference (Legacy)

Base URL: `http://localhost:8000/api`

## Authentication
Uses Bearer tokens (Supabase JWT).

Header:
`Authorization: Bearer <access_token>`

---

## Documents Router (`/api/documents`)

### 1. List Documents
- **Endpoint:** `GET /documents`
- **Query params:** `status`, `template`, `start_date`, `end_date`, `limit`, `offset`
- **Auth:** Optional (anonymous users receive empty list)

### 2. Upload Document
- **Endpoint:** `POST /documents/upload`
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file` (required)
  - `template` (optional)
  - `add_page_numbers` (optional)
  - `add_borders` (optional)
  - `add_cover_page` (optional)
  - `generate_toc` (optional)
  - `page_size` (optional)
- **Allowed file types:** `.docx, .pdf, .tex, .txt, .html, .htm, .md, .markdown, .doc`

### 3. Get Job Status
- **Endpoint:** `GET /documents/{job_id}/status`
- **Response:** job status, phase/current stage, progress percentage, messages, and per-phase updates

### 4. Submit Edit
- **Endpoint:** `POST /documents/{job_id}/edit`
- **Body:** JSON payload containing `edited_structured_data`

### 5. Get Preview Data
- **Endpoint:** `GET /documents/{job_id}/preview`
- **Response:** `structured_data`, `validation_results`, and metadata

### 6. Get Compare Data
- **Endpoint:** `GET /documents/{job_id}/compare`
- **Response:** HTML diff plus original/formatted data

### 7. Download Output
- **Endpoint:** `GET /documents/{job_id}/download`
- **Query:** `format=docx|pdf`
- **Response:** file stream

---

## Other API Routers
- `/api/auth/*` (signup/login/password reset/OTP)
- `/api/stream/*` (SSE stream updates)
- `/api/feedback/*`
- `/api/metrics/*`
