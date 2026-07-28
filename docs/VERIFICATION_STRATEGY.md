# ScholarFormAI Verification Strategy & Quality Assurance Architecture

**Date:** July 2026  
**Author:** Synthesis Engineering Team (`worker_synthesis`)  
**Target:** ScholarFormAI Monorepo (`backend/`, `frontend/`, `cli/`, `sdk/`, `.github/`)

---

## Executive Overview & Verification Mandate

This document defines the comprehensive, automated verification strategy for ScholarFormAI. It establishes a multi-tiered testing hierarchy, fixes existing test runner bottlenecks, specifies exact test suites to create for uncovered modules, and details CI/CD automated gating rules to ensure enterprise-grade quality throughout all refactoring phases.

### Integrity Mandate & Zero-Tolerance Policy
- **No Facades or Hardcoded Results:** All test cases must execute against real implementations or legitimate, state-maintaining mock double classes.
- **Strict Automated Verification:** Refactoring changes must pass all 5 verification tiers prior to merging into main branch.

---

## 1. Test Suite Infrastructure Repairs

Before expanding test coverage, three core infrastructure defects in the test execution runner must be resolved:

### 1.1 Repair Pytest Line Coverage `--cov` Tracking (`CRIT-05`)
- **Issue:** Running `pytest --cov=app` fails with `KeyError: 'pydantic.root_model'` during Pydantic v2.13+ import tracing.
- **Repair Implementation:** Update `backend/.coveragerc` to exclude dynamic Pydantic RootModel internal helpers and optimize coverage plugin hooks:
  ```ini
  [run]
  source = app
  omit =
      */pydantic/*
      app/models/root_model_helpers.py
      app/db/migrations/*

  [report]
  exclude_lines =
      pragma: no cover
      def __repr__
      raise NotImplementedError
      if __name__ == .__main__.:
      if TYPE_CHECKING:
  ```
- **Verification Command:** `pytest --cov=app --cov-report=term-missing` (must complete cleanly with 0 exceptions).

### 1.2 Eliminate Router Cold-Boot Test Collection Bottleneck (`HIGH-06`)
- **Issue:** Test collection in `pytest tests/` triggers sequential execution of `lazy_router_loader`, taking >600 seconds.
- **Repair Implementation:**
  1. Add a pytest fixture in `backend/tests/conftest.py` that initializes app router metadata once per test session:
     ```python
     @pytest.fixture(scope="session", autouse=True)
     def initialize_router_metadata():
         from app.main import app, _load_optional_routers
         _load_optional_routers(app)
     ```
  2. Optimize route loading logic in `main.py` so route discovery avoids redundant sub-module imports during collection.
- **Verification Command:** `pytest tests/ --collect-only` (must complete in < 15 seconds).

### 1.3 Fix Vitest Thread Isolation Failures (`MED-10`)
- **Issue:** 17 frontend Vitest test files leak module mock state and fail when executed in a single thread pool.
- **Repair Implementation:** Configure `frontend/vitest.config.js` to enforce process isolation:
  ```javascript
  import { defineConfig } from 'vitest/config';

  export default defineConfig({
    test: {
      pool: 'forks',
      environment: 'jsdom',
      globals: true,
      setupFiles: ['./src/test/setup.ts'],
    },
  });
  ```
- **Verification Command:** `npm test` in `frontend/` (must pass 100% of tests cleanly).

---

## 2. Multi-Tiered Verification Hierarchy

The ScholarFormAI testing model is structured into 5 distinct verification tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TIER 5: Adversarial & Security Coverage Hardening                      │
│ (Zip bombs, prompt injection, corrupt DOCX, zero-byte, RLS bypass)    │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 4: E2E User Flow Testing (Playwright Cross-Browser)               │
│ (Upload manuscript -> format -> preview diff -> download PDF/LaTeX)    │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 3: Performance, Load & Concurrency Testing                        │
│ (Locust stress testing, connection pool stability, memory leak audit)  │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 2: Component Integration Testing                                  │
│ (FastAPI TestClient, Supabase DB sessions, ChromaDB, Celery dispatch) │
├────────────────────────────────────────────────────────────────────────┤
│ TIER 1: Isolated Unit Testing                                          │
│ (Domain services, parsers, validators, style registry, SDK models)     │
└────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Isolated Unit Testing
- **Scope:** Pure functional units, domain logic, Pydantic schemas, text sanitization, parsing helpers.
- **Execution Target:** Fast execution (< 5 seconds for full suite). Zero network or database I/O allowed.

### Tier 2: Component Integration Testing
- **Scope:** FastAPI route handlers, database repositories (`SQLAlchemy` / `Supabase`), vector search (`ChromaDB`), background task dispatch (`Celery`).
- **Execution Target:** Uses mock containers or local test database. Executes in < 45 seconds.

### Tier 3: Performance & System Stress Testing
- **Scope:** High-concurrency document processing, connection pool saturation, async event loop blocking audits, memory consumption profiling.
- **Tools:** `locust -f tests/performance/locustfile.py`, `k6 run tests/performance/load_test.js`.

### Tier 4: E2E Browser Automation Testing
- **Scope:** End-to-end user journeys executed via Playwright in `frontend/e2e/`.
- **Scenarios:** Document upload, live split-editor diff preview, citation style switching, custom template selection, export download.

### Tier 5: Adversarial & Security Coverage Hardening
- **Scope:** Hardened boundary verification against security exploits and edge-case inputs:
  1. **Corrupt / Malformed `.docx` Files:** Truncated ZIP headers, missing `word/document.xml`.
  2. **Zip Bomb / Decompression Attacks:** Extremely high compression ratio nested archives.
  3. **Zero-Byte File Uploads:** Uploading empty 0-byte `.docx` or `.pdf` files.
  4. **Path Traversal Attacks:** Filenames containing `../../etc/passwd` or `C:\Windows\System32`.
  5. **Prompt Injection Payloads:** System prompt override attempts inside manuscript text sections.
  6. **Unauthenticated Webhook Tampering:** Forged HMAC signatures on `/api/v2/webhooks/receiver`.

---

## 3. Required Test Suites for Uncovered Modules & Core Services

To achieve true enterprise coverage, dedicated unit test files must be created for the **8 uncovered backend modules** and **core business services**:

### 3.1 New Backend Module Test Specifications

| # | Target Uncovered File | Required Test File Path | Key Test Cases & Coverage Mandate |
|---|---|---|---|
| 1 | `backend/app/db/base.py` | `backend/tests/unit/test_db_base.py` | Test Base model registration, metadata table binding, UUID column defaults. |
| 2 | `backend/app/models/suggestion.py` | `backend/tests/unit/test_model_suggestion.py` | Test `Suggestion` model instantiation, status transitions (pending -> applied -> rejected), dict serialization. |
| 3 | `backend/app/models/webhook.py` | `backend/tests/unit/test_model_webhook.py` | Test `WebhookEndpoint` URL validation, secret generation, failure count incrementing. |
| 4 | `backend/app/routers/v1/activity.py` | `backend/tests/integration/test_router_v1_activity.py` | Test `GET /api/v1/activity` with pagination, event filtering (upload, format, export), user isolation. |
| 5 | `backend/app/routers/v2/documents.py` | `backend/tests/integration/test_router_v2_documents.py` | Test v2 document upload, async status polling, structured JSON metadata response, error envelopes. |
| 6 | `backend/app/routers/v2/webhooks.py` | `backend/tests/integration/test_router_v2_webhooks.py` | Test webhook endpoint registration, event subscription updates, HMAC signature generation. |
| 7 | `backend/app/schemas/pagination.py` | `backend/tests/unit/test_schema_pagination.py` | Test `PaginatedResponse` schema with page limit, total items count, next/prev link calculation. |
| 8 | `backend/app/schemas/webhook.py` | `backend/tests/unit/test_schema_webhook.py` | Test `WebhookCreate` payload validation, URL format verification, secret length enforcement. |

### 3.2 Core Business Service Test Specifications

| Core Service File | Required Test File Path | Key Test Cases & Coverage Mandate |
|---|---|---|
| `backend/app/services/formatter.py` | `backend/tests/unit/test_formatter_deep.py` | Test OpenXML layout generation, margin settings, font application, citation reference assembly, running header, page estimation logic. |
| `backend/app/services/parser.py` | `backend/tests/unit/test_parser_deep.py` | Test manuscript section parsing, author extraction, abstract parsing, reference list parsing, malformed text handling. |
| `backend/app/services/validator.py` | `backend/tests/unit/test_validator_deep.py` | Test style rule validation (APA, MLA, IEEE), missing section reporting, citation style compliance checks. |
| `backend/app/services/style_registry.py` | `backend/tests/unit/test_style_registry.py` | Test built-in style registration (`apa`, `mla`, `ieee`), custom style registration, thread-safe style retrieval. |

### 3.3 SDK & CLI Test Specifications

| Target Component | Required Test File Path | Key Test Cases & Coverage Mandate |
|---|---|---|
| `sdk/amf_sdk/async_client.py` | `sdk/tests/test_async_client.py` | Test `AsyncAMFClient` async request handling, context manager (`async with`), retries, status error mappings (400, 401, 404, 429, 500). |
| `cli/amf/commands/update.py` & `issue.py` | `cli/tests/test_cli_commands.py` | Test CLI `amf update` subcommands (8 commands), `amf issue` subcommands (8 commands), config loading, offline fallback. |
| `frontend/src/components/*.tsx` | `frontend/src/test/components/*.test.tsx` | Test `.tsx` UI components (`FormattingOptions.tsx`, `ManuscriptInput.tsx`, `ErrorDialog.tsx`) under Vitest + React Testing Library. |

---

## 4. CI/CD Automated Gating & Quality Controls

To prevent regression during refactoring, GitHub Actions workflows (`.github/workflows/`) and pre-commit hooks (`.pre-commit-config.yaml`) enforce the following automated gates:

```
[ Git Push / PR ] ──→ [ Pre-Commit Hooks ] (Ruff, Detect-Secrets, Typecheck)
                       │
                       ▼
                 [ GitHub Actions CI ]
                       ├── Gate 1: Lint & Static Analysis (Ruff, ESLint --ext js,jsx,ts,tsx)
                       ├── Gate 2: Backend Pytest Suite (100% pass, coverage > 90%)
                       ├── Gate 3: SDK & CLI Pytest Suite (100% pass)
                       ├── Gate 4: Frontend Vitest Suite (--pool=forks, 100% pass)
                       └── Gate 5: Security & Secret Scan (.secrets.baseline hash audit)
```

### Pre-Commit Configuration Updates
Update `.pre-commit-config.yaml` to include explicit TypeScript linting and API key baseline checks:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### Verification Command Cheatsheet

```powershell
# 1. Run Backend Unit Tests & Coverage Report
cd backend; pytest --cov=app --cov-report=term-missing

# 2. Run Frontend Unit Tests with Isolated Pool
cd frontend; npm test

# 3. Run CLI & SDK Test Suites
cd cli; pytest tests/
cd sdk; pytest tests/

# 4. Run Frontend E2E Playwright Tests
cd frontend; npm run test:e2e

# 5. Run Security & Secret Baseline Check
detect-secrets scan --baseline .secrets.baseline
```
