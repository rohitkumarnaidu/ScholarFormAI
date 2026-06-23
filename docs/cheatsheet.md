<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Quick Reference
description: One-page cheatsheet for common commands and key information
sidebar_position: 95
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: monthly
last_updated: June 2026
---

# Quick Reference

## Local Development

```bash
# Backend
cd backend && python -m venv .venv && .\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Docs
http://localhost:8000/docs           # Swagger UI
http://localhost:3000                 # Frontend
http://localhost:8000/api/v1/health  # Health check
```

## Tests

```bash
# Backend (fast, no services)
pytest tests -m "not integration and not llm and not contract" -x -q

# Backend (deep coverage)
pytest tests/test_formatter_deep.py -v

# Frontend unit tests
npm test                    # vitest
npm run lint                # eslint
npm run test:e2e            # Playwright headless

# Full CI pipeline (order)
ruff check app && mypy app && pytest tests -m "not integration and not llm"
```

## Lint & Type

```bash
ruff check app --config ruff.toml && ruff format app --check
mypy --config-file mypy.ini app          # continues on error
cd frontend && npm run lint              # eslint --max-warnings 0
```

## Docker

```bash
cd backend/docker
docker compose up -d                     # GROBID + services
docker compose down                      # Stop all
```

## Database

```bash
alembic upgrade head                     # Run pending migrations
alembic revision --autogenerate -m "msg" # Create migration
pg_dump $SUPABASE_DB_URL --format=custom --file=backup.dump
```

## Git

```bash
git checkout -b feature/my-feature
git commit -m "feat: my feature description"
git push origin feature/my-feature
```

## Key URLs

| Resource | URL |
|----------|-----|
| Backend API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| Frontend | `http://localhost:3000` |
| Health Check | `http://localhost:8000/api/v1/health/live` |
| Production API | `https://api.scholarform.ai` |
| Production App | `https://scholarform.ai` |

## Quick API Calls

```bash
# Health
curl http://localhost:8000/api/v1/health

# List templates
curl http://localhost:8000/api/v1/templates

# Upload document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@paper.docx" -F "template=ieee"

# Check status
curl http://localhost:8000/api/v1/documents/{job_id}/status \
  -H "Authorization: Bearer $TOKEN"

# Download
curl -o formatted.docx \
  http://localhost:8000/api/v1/documents/{job_id}/download?format=docx \
  -H "Authorization: Bearer $TOKEN"
```
