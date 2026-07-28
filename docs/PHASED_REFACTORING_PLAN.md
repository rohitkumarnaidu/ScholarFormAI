# ScholarFormAI Phased Refactoring Plan & Architecture Modernization Strategy

**Date:** July 2026  
**Author:** Synthesis Engineering Team (`worker_synthesis`)  
**Target:** ScholarFormAI Monorepo (`backend/`, `frontend/`, `cli/`, `sdk/`, `deploy/`, `docs/`)

---

## Executive Overview & Architectural Principles

This document presents a concrete, 4-phase technical refactoring plan designed to transform ScholarFormAI into an open-source, enterprise-grade academic manuscript processing platform. The refactoring strategy prioritizes:

1. **Clean Architecture & Domain Boundary Separation:** Decoupling FastAPI HTTP routing from domain services, database models, and external microservice clients.
2. **SOLID & DRY Principles:** Breaking down God classes, enforcing Dependency Inversion (DIP), and eliminating duplicated layout/export logic.
3. **Data Integrity & Zero Data Loss:** Eliminating payload truncation defects and ensuring reliable database session handling.
4. **Comprehensive Testability & CI Reliability:** Resolving test runner bottlenecks, repairing coverage measurement tools, and filling coverage gaps across core modules.
5. **Open-Source Enterprise Readiness:** Standardizing documentation, container security, licensing headers, and developer onboarding workflows.

---

## Refactoring Roadmap Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: Immediate Critical Bug Fixes & Security Hardening             │
│ - Unmounted routes, DB leaks, SDK NameError, Docker user permissions,  │
│   text sanitization line-break preservation, temp file cleanup          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: Domain Decoupling & Clean Architecture Restructuring          │
│ - Decompose documents_impl.py into application services                │
│ - Decompose ManuscriptFormatter God class                              │
│ - Decouple core services from Pydantic API models                      │
│ - Consolidate frontend App Router & single API service client           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: Infrastructure, Test Strategy & Performance Optimization      │
│ - Eliminate router cold-boot test collection bottleneck (>600s)         │
│ - Fix Pydantic --cov coverage tracking error                           │
│ - Replace CLI busy polling with watchdog events                        │
│ - Persist vector store TTL timers & fix Vitest thread pool config       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: Open-Source Enterprise Readiness & Documentation Alignment    │
│ - Synchronize AGENTS.md, API_REFERENCE.md, ERROR_CODES.md, RAG.md      │
│ - Replace icon font tags with lucide-react SVGs                        │
│ - Align style registry constants & auto-generate OpenAPI specs          │
│ - Purge legacy build artifacts & obsolete scripts                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Immediate Critical Bug Fixes & Security Hardening

**Goal:** Resolve severe runtime defects, data loss bugs, container startup crashes, and resource leaks that impact production stability.

### Task 1.1: Mount or Refactor Unmounted API Routes (`CRIT-01`)
- **Target Files:** `backend/app/main.py`, `backend/app/api/routes.py`
- **Refactoring Strategy:**
  1. Inspect `app/api/routes.py` endpoints (`/format`, `/validate`, `/preview`, `/styles`).
  2. Deprecate legacy endpoints in `routes.py` and redirect calls to the active v1 router under `/api/v1/documents/upload` and `/api/v1/templates/`.
  3. Fix `download_url` path generation to return valid signed URLs (`/api/v1/documents/{jobId}/download`) instead of orphaned paths (`/api/v1/download/{filename}`).
- **Verification:** Execute `curl -X POST http://localhost:8000/api/v1/documents/upload` and confirm correct endpoint routing.

### Task 1.2: Fix DB Generator Connection Leaks (`CRIT-02`)
- **Target Files:** `backend/app/services/llm_fallback_service.py`, `backend/app/services/llm_key_service.py`
- **Refactoring Strategy:**
  Replace `next(get_db())` calls with explicit context managers:
  ```python
  # BEFORE (leaks DB connection generator):
  db: Session = next(get_db())

  # AFTER (safely closes connection upon completion):
  from app.db.session import SessionLocal

  with SessionLocal() as db:
      # Perform database operations
  ```
- **Verification:** Run load test on LLM provider key fetching and verify connection pool count remains stable in PostgreSQL metrics.

### Task 1.3: Preserve Line-Breaks in Text Sanitization (`CRIT-03`)
- **Target File:** `frontend/src/services/api.core.js`
- **Refactoring Strategy:**
  Update `removeControlChars` in `api.core.js` to explicitly preserve whitespace control characters (`\n` ASCII 10, `\r` ASCII 13, `\t` ASCII 9):
  ```javascript
  // BEFORE (strips all characters with ASCII < 32):
  const removeControlChars = (input) => (
      Array.from(String(input ?? ''))
          .filter((char) => {
              const code = char.charCodeAt(0);
              return code >= 32 && code !== 127;
          })
          .join('')
  );

  // AFTER (preserves newlines and tabs):
  const removeControlChars = (input) => (
      Array.from(String(input ?? ''))
          .filter((char) => {
              const code = char.charCodeAt(0);
              return (code >= 32 && code !== 127) || code === 10 || code === 13 || code === 9;
          })
          .join('')
  );
  ```
- **Verification:** Unit test `removeControlChars("Line 1\nLine 2\tIndented")` and assert output retains `\n` and `\t`.

### Task 1.4: Fix Python SDK `AMFError` Exception Import (`CRIT-04`)
- **Target File:** `sdk/amf_sdk/client.py`
- **Refactoring Strategy:**
  Add `AMFError` to exception imports in `client.py`:
  ```python
  from amf_sdk.exceptions import (
      AMFError,  # Fixed missing base exception import
      AuthenticationError,
      NotFoundError,
      RateLimitError,
      ServerError,
      ValidationError,
  )
  ```
- **Verification:** Mock a 500 status response in `sdk/tests/test_client.py` and verify `AMFError` or `ServerError` is raised instead of `NameError`.

### Task 1.5: Fix Non-Root Container Permissions Crash (`HIGH-05`)
- **Target File:** `backend/Dockerfile`
- **Refactoring Strategy:**
  Copy dependencies into `/home/amf/.local` with explicit ownership for user `amf`:
  ```dockerfile
  # BEFORE:
  COPY --from=builder /root/.local /root/.local
  USER amf

  # AFTER:
  COPY --from=builder --chown=amf:amf /root/.local /home/amf/.local
  ENV PATH=/home/amf/.local/bin:$PATH
  USER amf
  ```
- **Verification:** Build and run container as non-root user `amf` (`docker run --rm amf-backend python -c "import app.main"`) and verify clean execution.

### Task 1.6: Temporary File Cleanup in Document Formatting (`MED-01`)
- **Target File:** `backend/app/api/routes.py`
- **Refactoring Strategy:**
  Wrap formatting execution in `try ... finally` blocks or add a FastAPI `BackgroundTasks` cleanup handler to remove temporary `.docx` files upon HTTP response delivery.

---

## Phase 2: Domain Decoupling & Clean Architecture Restructuring

**Goal:** Decompose monolithic code structures, separate application concerns, and enforce SOLID design principles.

### Task 2.1: Decompose 1,350-Line `documents_impl.py` Monolith (`HIGH-01`)
- **Target File:** `backend/app/routers/v1/documents_impl.py`
- **Refactoring Strategy:**
  Decompose `documents_impl.py` into dedicated application service classes under `backend/app/services/`:
  1. `DocumentPipelineService`: Orchestrates virus scanning, magic byte checking, pipeline execution, and Celery dispatch.
  2. `DocumentCrudService`: Handles metadata querying, status updates, and Supabase database interactions.
  3. `DocumentExportService`: Manages PDF/LaTeX/JATS compilation and download URL token generation.
- **Architecture View:**
  ```
  [ FastAPI Route Handler ] ──→ [ DocumentPipelineService ] ──→ [ PipelineOrchestrator ]
                            ──→ [ DocumentCrudService ]     ──→ [ Supabase / DB ]
                            ──→ [ DocumentExportService ]   ──→ [ Exporters (PDF/LaTeX) ]
  ```

### Task 2.2: Decompose `ManuscriptFormatter` God Class (`HIGH-01`)
- **Target File:** `backend/app/services/formatter.py`
- **Refactoring Strategy:**
  Split `ManuscriptFormatter` into four single-responsibility classes:
  1. `DocumentLayoutEngine`: OpenXML document margins, typography, page setup, and section styling.
  2. `ReferenceRenderer`: CSL citation list string formatting and bibliography rendering.
  3. `PageEstimator`: In-memory paragraph and page calculation without re-reading files from disk.
  4. `HTMLPreviewRenderer`: Plaintext/HTML preview generation.

### Task 2.3: Decouple Core Business Services from Pydantic API Models (`HIGH-02`)
- **Target Files:** `backend/app/domain/models.py`, `backend/app/services/formatter.py`, `parser.py`, `validator.py`
- **Refactoring Strategy:**
  Define plain Python dataclasses in `app/domain/models.py` (`DomainManuscript`, `DomainAuthor`, `DomainSection`, `DomainReference`).
  Modify business services to operate exclusively on domain dataclasses. Convert HTTP Pydantic request/response models to domain dataclasses at the router layer interface.

### Task 2.4: Consolidate Frontend App Router & Unify API Client (`HIGH-03`, `MED-04`)
- **Target Files:** `frontend/src/app/`, `frontend/app/`, `frontend/tsconfig.json`, `frontend/src/lib/api.ts`
- **Refactoring Strategy:**
  1. Remove or migrate dead TypeScript pages in `frontend/src/app/` into `frontend/app/`.
  2. Standardize all `frontend/app/` pages on `.tsx` components and remove `"src/app"` from `tsconfig.json` exclude list.
  3. Deprecate 19 untyped JavaScript service modules in `frontend/src/services/` and standardize UI component data fetching on `frontend/src/lib/api.ts` with strongly typed request/response interfaces.

---

## Phase 3: Infrastructure, Test Strategy & Performance Optimization

**Goal:** Eliminate test runner collection bottlenecks, repair coverage tooling, optimize system resource utilization, and eliminate thread leaks.

### Task 3.1: Eliminate Router Cold-Boot Test Collection Bottleneck (`HIGH-06`)
- **Target File:** `backend/app/main.py`
- **Refactoring Strategy:**
  Refactor `_ensure_routers_loaded()` in `main.py` to pre-register routes during application instantiation while maintaining lightweight router metadata initialization. This reduces full test suite collection time from >600s down to under 15 seconds.

### Task 3.2: Repair Pytest `--cov` Coverage Tracking (`CRIT-05`)
- **Target Files:** `backend/pytest.ini`, `.coveragerc`
- **Refactoring Strategy:**
  Update coverage configuration in `.coveragerc` to exclude dynamic Pydantic v2 `RootModel` internal generators:
  ```ini
  [coverage:run]
  omit =
      */pydantic/*
      app/models/root_model_helpers.py
  ```
  Ensure `pytest --cov=app --cov-report=term-missing` runs cleanly without raising `KeyError: 'pydantic.root_model'`.

### Task 3.3: Replace CLI Busy Polling with `watchdog` (`MED-07`)
- **Target File:** `cli/amf/commands/format.py`
- **Refactoring Strategy:**
  Replace `while True: time.sleep(1)` loop in CLI watch mode with `watchdog.observers.Observer` file system event handlers, eliminating unnecessary CPU wakeups and disk read IOPS.

### Task 3.4: Persist Session Vector Store TTL Timers (`MED-08`)
- **Target File:** `backend/app/services/session_vector_store.py`
- **Refactoring Strategy:**
  Replace volatile in-memory `threading.Timer` / `asyncio.create_task` TTL deletion with Redis TTL keys or a Celery beat scheduled cleanup task (`purge_expired_vector_sessions`), ensuring vector store cleanup survives server restarts.

### Task 3.5: Fix Vitest Thread Pool Configuration (`MED-10`)
- **Target Files:** `frontend/vitest.config.js`, `frontend/package.json`
- **Refactoring Strategy:**
  Update Vitest configuration in `vitest.config.js` to set pool execution to `fork`:
  ```javascript
  export default defineConfig({
    test: {
      pool: 'forks',
      environment: 'jsdom',
    },
  });
  ```
  This ensures isolated process state per test file, resolving the 17 test file failures.

### Task 3.6: Prevent Event Loop Blocking in Async Endpoints (`MED-02`)
- **Target Files:** `backend/app/api/routes.py`, `backend/app/routers/v1/documents_impl.py`
- **Refactoring Strategy:**
  Wrap heavy synchronous OpenXML writing and `difflib.HtmlDiff` processing in `asyncio.to_thread(...)`:
  ```python
  html_diff = await asyncio.to_thread(
      difflib.HtmlDiff(wrapcolumn=80).make_file,
      original_text,
      formatted_text
  )
  ```

---

## Phase 4: Open-Source Enterprise Readiness & Documentation Alignment

**Goal:** Synchronize documentation, enforce UI accessibility standards, auto-generate API client SDKs, and prepare repository for open-source contributors.

### Task 4.1: Synchronize System Documentation (`HIGH-07`)
- **Target Files:** `AGENTS.md`, `API_REFERENCE.md`, `ERROR_CODES.md`, `RAG.md`, `AI.md`
- **Refactoring Strategy:**
  1. Update `AGENTS.md`: Correct project root reference to `ScholarFormAI` and replace dead paths (`backend/app/api/routes.py`) with active router paths (`backend/app/routers/v1/documents.py`).
  2. Update `API_REFERENCE.md`: Document actual endpoints (`POST /api/v1/documents/upload`, `GET /api/v1/templates/`, `GET /api/v1/documents/{jobId}/download`).
  3. Update `ERROR_CODES.md`: Align error code tables with FastAPI envelope exceptions (`INVALID_UPLOAD_REQUEST`, `DOCUMENT_VALIDATION_FAILED`).
  4. Update `RAG.md` and `AI.md`: Reflect implemented LiteLLM 4-tier fallback chain and ChromaDB vector search.

### Task 4.2: Replace Material Symbols Font Tags with `lucide-react` (`MED-05`)
- **Target Files:** `frontend/src/components/FileUpload.jsx`, `BatchUploadPanel.jsx`, `Preview.jsx`, `Stepper.jsx`, `SplitEditor.jsx`
- **Refactoring Strategy:**
  Replace Google Material Symbols font tags (`<span className="material-symbols-outlined">cloud_upload</span>`) with native SVG icons imported from `lucide-react` (`<Upload className="w-5 h-5" />`). Fix HTML nesting in `FileUpload.jsx` by converting outer `<div role="button">` to a non-interactive wrapper.

### Task 4.3: Synchronize Style Registry Constants (`MED-06`)
- **Target Files:** `frontend/src/lib/constants.ts`, `backend/app/services/style_registry.py`
- **Refactoring Strategy:**
  Align frontend style constants in `constants.ts` with backend internal IDs (`apa`, `mla`, `ieee`, `chicago`, `harvard`, `vancouver`, `acs`, `ama`).

### Task 4.4: OpenAPI Client Spec Auto-Generation & SPDX Licensing
- **Target Files:** `backend/app/main.py`, `cli/`, `sdk/`
- **Refactoring Strategy:**
  1. Add an automated script/CI step (`scripts/generate_openapi.py`) to dump `openapi.json` directly from FastAPI `app.openapi()`.
  2. Add standard SPDX License Headers (`# SPDX-License-Identifier: MIT`) to all Python files in `cli/` and `sdk/`.

### Task 4.5: Purge Legacy Build Artifacts & Obsolete Scripts
- **Target Files:** `backend/scripts/fix_all_broken_pipeline_tests.py`, `frontend/dist/`
- **Refactoring Strategy:**
  Delete obsolete fix script and remove legacy Vite `dist/` directory from git tracking.

---

## Refactoring Verification Gate Summary

| Phase | Milestone | Primary Output | Gate Criterion |
|---|---|---|---|
| **Phase 1** | Critical Bug Fixes | Fixed SDK, Docker, DB Leaks, Sanitization | All critical bugs fixed, container builds non-root, sanitization retains `\n` |
| **Phase 2** | Domain Decoupling | Clean Architecture backend & unified TS frontend | `documents_impl.py` decomposed, frontend standardized on `app/*.tsx` |
| **Phase 3** | Infra & Performance | Optimized pytest & Vitest runners | `pytest tests/` collection < 15s, `--cov` passes, Vitest 100% pass |
| **Phase 4** | Open-Source Readiness | Synchronized docs & clean repo | `AGENTS.md` & `API_REFERENCE.md` accurate, zero obsolete build artifacts |
