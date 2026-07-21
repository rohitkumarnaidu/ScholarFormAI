# ScholarForm AI — Testing Guide

> **Quick reference.** For the full testing strategy (195 lines), see [docs/Testing.md](docs/Testing.md).

---

## Test Suites Overview

| Suite | Tool | Location | Command |
|-------|------|----------|---------|
| Backend unit | pytest | `backend/tests/` | `pytest tests -m "not integration and not llm"` |
| Backend integration | pytest | `backend/tests/` | `pytest tests -m integration` |
| Backend LLM | pytest | `backend/tests/` | `pytest tests -m llm` |
| Frontend unit | Vitest | `frontend/src/` | `npm test` |
| Frontend E2E | Playwright | `frontend/e2e/` | `npm run test:e2e` |

---

## Backend

### Prerequisites
- Python 3.12.x (not 3.11, not 3.13+)
- Virtual environment activated (`backend/.venv`)
- Dependencies installed: `pip install -r requirements-dev.txt`

### Running Tests

```bash
cd backend

# Fast tests only (no external services) — ~45s
pytest tests -m "not integration and not llm and not contract" -x -q

# With coverage report
pytest tests -m "not integration and not llm" --cov=app --cov-report=term

# Single test file
pytest tests/test_document_service_deep.py -v --tb=short

# Full suite (all services running — ~6m)
pytest

# Lint and type check
ruff check app --config ruff.toml
mypy --config-file mypy.ini app
```

### Test Markers

| Marker | Requires | Speed |
|--------|----------|-------|
| `unit` | Nothing | Fast |
| `integration` | Docker (Redis, DB, GROBID) | Medium |
| `llm` | Live LLM API key | Slow |
| `service` | Full stack | Slow |
| `contract` | Running FastAPI | Medium |

### Deep Tests

Enterprise-grade test files with intensive mocking target >80% per-module coverage:

| Module | File | Tests | Coverage |
|--------|------|-------|----------|
| DocxParser | `test_docx_parser_deep.py` | 108 | ~90% |
| Formatter | `test_formatter_deep.py` | 207 | ~88% |
| PipelineOrchestrator | `test_pipeline_orchestrator_deep.py` | 49 | ~82% |
| Classifier | `tests/classifier/test_classifier_deep.py` | 92 | ~86% |
| DocumentService | `test_document_service_deep.py` | 110 | 86% |
| ReasoningEngine | `test_reasoning_engine_deep.py` | 87 | 80% |
| AgentPipeline | `test_agent_deep.py` | 120 | ~84% |
| PdfParser | `test_pdf_parser_deep.py` | 71 | 88% |
| RagEngine | `test_rag_engine_deep.py` | 87 | 91% |

### Coverage Requirements
- Project-wide minimum: **70%** (enforced in CI)
- Per-module deep tests: **>80%**
- New features must include corresponding tests

---

## Frontend

### Prerequisites
- Node.js 20+ (LTS)
- `npm install` completed
- `npm install @testing-library/dom --save-dev` (common missing dep)

### Running Tests

```bash
cd frontend

# Vitest unit tests — ~15s
npm test
# or
npx vitest

# With UI
npx vitest --ui

# Playwright E2E (requires running backend)
npm run test:e2e           # headless
npm run test:e2e:headed    # headed (visible browser)

# Lint
npm run lint
npx tsc --noEmit
```

### Critical Test Paths

| # | Flow | File |
|---|------|------|
| 1 | Guest upload → process → download | `e2e/upload-journey.spec.js` |
| 2 | Auth: signup → login → dashboard | `e2e/auth-flow.spec.js` |
| 3 | Template selection → DOCX export | `e2e/formatter-upload.spec.js` |
| 4 | Live preview WebSocket | `e2e/formatter-live-preview.spec.js` |
| 5 | Agent chat → outline → approve | `e2e/generator-outline-approve.spec.js` |
| 6 | Multi-doc synthesis SSE stream | `e2e/generator-synthesis.spec.js` |

---

## CI Pipeline

| Workflow | Triggers | Steps |
|----------|----------|-------|
| `backend-ci.yml` | PR + push to main | ruff → mypy → pytest (fast) |
| `frontend-ci.yml` | PR + push to main | eslint → vitest → build → Playwright |
| `security.yml` | PR + push to main | pip-audit, npm audit, Trivy, CodeQL |
| `dependency-review.yml` | PR to main | License + vulnerability check |

---

## Adding New Tests

### Backend
1. Place test files in `backend/tests/` matching the module path
2. Use `_deep.py` suffix for intensive mocking tests
3. Use `_test.py` suffix for standard tests
4. Mark integration/LLM/service tests with `@pytest.mark.*`
5. Create subdirectory `conftest.py` for isolated fixtures

### Frontend
1. Place test files next to source files (Vitest convention)
2. Use `*.test.tsx` naming
3. E2E tests go in `frontend/e2e/`
4. Use Playwright fixtures for auth state

---

*Last updated: July 2026*
