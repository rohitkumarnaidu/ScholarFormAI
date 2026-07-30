<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: Scholarform Grobid
emoji: "🌍"
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Scholarform GROBID Space Template

Docker-based GROBID template with a lightweight proxy on port `7860` for Hugging Face Spaces.

## Endpoints

- `GET /api/isalive`
- `POST /api/processHeaderDocument`
- `POST /api/processFulltextDocument`

## Files

- `Dockerfile`
- `grobid.yaml`
- `proxy.py`
- `start.sh`
