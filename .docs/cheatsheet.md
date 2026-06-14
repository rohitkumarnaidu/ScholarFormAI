---
title: ScholarForm AI — Cheatsheet
description: Quick reference for common commands, workflows, and API conventions
sidebar_position: 95
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: monthly
last_updated: June 2026
---

# Cheatsheet

## Backend Commands

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Testing
pytest tests -m "not integration and not llm and not contract" -x -q
pytest tests -m "contract" -x -v
pytest tests -m "integration" --timeout=30

# Lint/type
ruff check app --config ruff.toml
mypy --config-file mypy.ini app

# Database
alembic upgrade head
alembic revision --autogenerate -m "message"
alembic downgrade -1

# Celery
celery -A app.tasks.celery_tasks worker -Q interactive,batch
```

## Frontend Commands

```bash
# Development
npm run dev            # next dev --turbopack

# Testing
npm run test           # vitest
npm run test:e2e       # headless Playwright
npm run test:e2e:headed
npm run lint           # eslint --max-warnings 0

# Build
npm run build
```

## Git Workflow

```bash
# Pre-commit hooks auto-run: ruff, ruff-format, eslint, detect-secrets, version-consistency
git add <files>
git commit

# Version sync (canonical source: pyproject.toml)
python scripts/sync_version.py
python scripts/sync_version.py --check
```

## CI Pipeline

`ruff (E9,F63,F7,F82)` → `mypy (continue-on-error)` → `pytest (skip integration & slow)`

## Environment Setup

```bash
# Backend
cp backend/.env.example backend/.env
python scripts/generate_env_template.py

# Frontend
cp frontend/.env.example frontend/.env.local
```

## Key URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/v1/health |

## API Conventions

```
Route pattern: /api/v1/{resource}[/{id}][/{action}]
```

```json
{
  "data": { ... },
  "error": null,
  "request_id": "uuid-here",
  "timestamp": "2026-06-14T10:00:00Z"
}
```

## See Also

- [Glossary](glossary.md)
- [Getting Started](content/Getting Started.md)
