<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Scholarform Nougat Service
emoji: 📄
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Scholarform Nougat Service

## Endpoints
- `GET /` - status + model info
- `GET /health` - health check
- `POST /parse` - multipart upload (`file`) for PDF parsing

## Optional Space Variables
- `NOUGAT_MODEL` (default: `facebook/nougat-small`)
- `NOUGAT_MAX_PAGES` (default: `30`)
- `NOUGAT_MAX_TOKENS` (default: `4096`)

Use the same code for both `primary` and `shadow` Spaces.
