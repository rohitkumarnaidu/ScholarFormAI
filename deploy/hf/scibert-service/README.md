<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Scholarform SciBERT Service
emoji: 🧠
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Scholarform SciBERT Service

## Endpoints
- `GET /` - status + model info
- `GET /health` - health check
- `POST /predict` - JSON body: `{"texts": ["...", "..."]}`

## Optional Space Variables
- `SCIBERT_MODEL` (default: `allenai/scibert_scivocab_uncased`)
- `SCIBERT_MAX_LENGTH` (default: `512`)

Use the same code for both `primary` and `shadow` Spaces.
