# ScholarFormAI Risk & Technical Debt Report

**Date:** July 2026  
**Author:** Synthesis Engineering Team (`worker_synthesis`)  
**Target:** ScholarFormAI Monorepo (`backend/`, `frontend/`, `cli/`, `sdk/`, `deploy/`, `.github/`, `docs/`)

---

## Executive Summary

This report provides a complete, structured catalog of technical debt (TD-001 through TD-025) and an Enterprise Risk Register for ScholarFormAI. It evaluates security vulnerabilities, data loss defects, availability bottlenecks, maintainability friction, and open-source community onboarding risks across all monorepo domains.

---

## 1. Technical Debt Catalog (TD-001 through TD-025)

The table below catalogs all identified technical debt items, including their impact, severity level, affected file locations, architecture category, and estimated remediation effort (in story points / hours).

| Debt ID | Debt Title | Impact Summary | Severity | Affected File(s) | Category | Remediation Effort |
|---|---|---|---|---|---|---|
| **TD-001** | Unmounted Core API Routes | Legacy `/format`, `/validate`, `/styles` endpoints in `api/routes.py` return 404 because they are unmounted in `main.py`. | **Critical** | `backend/app/main.py:262-274`, `backend/app/api/routes.py` | Architecture | 4 hrs (0.5 SP) |
| **TD-002** | Generator DB Session Leaks | `next(get_db())` yields session without advancing generator, skipping `finally: db.close()`. | **Critical** | `backend/app/services/llm_fallback_service.py:207`, `llm_key_service.py:64` | Database | 2 hrs (0.25 SP) |
| **TD-003** | Pytest `--cov` Coverage Failure | Running `pytest --cov` crashes with `KeyError: 'pydantic.root_model'`, breaking CI coverage tracking. | **Critical** | `backend/pytest.ini`, `.coveragerc` | Testing | 6 hrs (0.75 SP) |
| **TD-004** | Monolithic `documents_impl.py` | 1,350-line procedural file combines HTTP routing, virus scanning, magic bytes, Redis caching, and export. | **High** | `backend/app/routers/v1/documents_impl.py` | Clean Code | 16 hrs (2 SP) |
| **TD-005** | `ManuscriptFormatter` God Class | Combined margin, font, header, abstract, OpenXML page number, estimation, and HTML preview in 1 class. | **High** | `backend/app/services/formatter.py:17-357` | SOLID (SRP) | 12 hrs (1.5 SP) |
| **TD-006** | Service Coupling to Pydantic API Models | Business services import HTTP response models (`Manuscript`, `Author`, `Section`) directly from `app.api.models`. | **High** | `backend/app/services/formatter.py:11`, `parser.py:4`, `validator.py:4` | SOLID (DIP) | 8 hrs (1 SP) |
| **TD-007** | Temporary `.docx` File Accumulation | `/format` creates temporary files with `delete=False` without unlinking after HTTP response delivery. | **High** | `backend/app/api/routes.py:39-43` | Resource Leak | 3 hrs (0.5 SP) |
| **TD-008** | Async Event Loop Blocking | Heavy CPU/IO (`python-docx` building, `difflib.HtmlDiff`) runs synchronously inside `async def` routes. | **High** | `backend/app/api/routes.py:32`, `backend/app/routers/v1/documents_impl.py:988` | Performance | 6 hrs (0.75 SP) |
| **TD-009** | Architecture Duality in DB Access | System mixes `supabase-py` PostgREST HTTP client with SQLAlchemy ORM engine and migrations. | **Medium** | `backend/app/db/supabase_client.py`, `backend/app/db/session.py` | Architecture | 16 hrs (2 SP) |
| **TD-010** | Text Sanitization Newline Stripping | `removeControlChars` filters ASCII `< 32`, silently removing `\n`, `\r`, `\t` from uploaded manuscripts. | **Critical** | `frontend/src/services/api.core.js:48-55` | Data Loss | 2 hrs (0.25 SP) |
| **TD-011** | Dual Frontend App Router | Inactive TypeScript router in `frontend/src/app` excluded in `tsconfig.json` while active JS router lives in `app/`. | **High** | `frontend/src/app/`, `frontend/tsconfig.json:51` | Architecture | 8 hrs (1 SP) |
| **TD-012** | Dual API Service Layers | Strongly typed `src/lib/api.ts` is ignored by UI components in favor of 19 untyped `src/services/*.js` files. | **Medium** | `frontend/src/lib/api.ts`, `frontend/src/services/` | Code Quality | 12 hrs (1.5 SP) |
| **TD-013** | ESLint Ignores TypeScript & Disables Hooks | ESLint CLI targets `--ext js,jsx` only, `@typescript-eslint` is absent, and React Hooks rules are turned off. | **High** | `frontend/package.json:13`, `frontend/eslint.config.js:18-25` | Tooling / QA | 6 hrs (0.75 SP) |
| **TD-014** | Accessibility Nesting & Font Dependencies | `<button>` inside `<div role="button">` in `FileUpload.jsx`; Material Symbols font tags used instead of SVGs. | **Medium** | `frontend/src/components/FileUpload.jsx`, `Preview.jsx` | Accessibility | 8 hrs (1 SP) |
| **TD-015** | Citation Style Constant Mismatches | `constants.ts` format strings (`Author-Year`) mismatch backend internal style codes (`apa`, `ieee`). | **Medium** | `frontend/src/lib/constants.ts:1-11`, `style_registry.py:46-240` | Consistency | 4 hrs (0.5 SP) |
| **TD-016** | SDK `AMFError` Exception Missing Import | `AMFError` is unimported in `client.py:62`, causing `NameError` on HTTP 500 or 502 server errors. | **Critical** | `sdk/amf_sdk/client.py:62` | Runtime Defect | 1 hr (0.125 SP) |
| **TD-017** | SDK Missing Retry & Async Tests | `AMFClient` lacks automated retry middleware; `sdk/tests/test_client.py` has no async or error tests. | **High** | `sdk/amf_sdk/client.py`, `sdk/tests/` | Reliability | 8 hrs (1 SP) |
| **TD-018** | CLI Watch Mode Busy Polling | `_format_and_watch` uses `while True: time.sleep(1)` loop querying `stat().st_mtime` instead of file events. | **Medium** | `cli/amf/commands/format.py:68-74` | Performance | 4 hrs (0.5 SP) |
| **TD-019** | Docker Container Permission Crash | `Dockerfile` copies `/root/.local` to non-root user `amf`, causing permission denied crash on strict OCI runtime. | **High** | `backend/Dockerfile:13-25` | Container Sec | 2 hrs (0.25 SP) |
| **TD-020** | In-Memory Vector Store TTL Timers | Ephemeral ChromaDB TTL deletion uses in-memory timers (`threading.Timer`), lost on process restart. | **Medium** | `backend/app/services/session_vector_store.py:117-131` | Storage Leak | 6 hrs (0.75 SP) |
| **TD-021** | Router Load Test Collection Timeout | Sequential lazy router loading causes `pytest tests/` test suite collection to exceed 600s timeout. | **High** | `backend/app/main.py:687-695`, `TECHNICAL_DEBT.md` | Test Bottleneck | 8 hrs (1 SP) |
| **TD-022** | 8 Untested Backend Modules | 8 backend files (`routers/v2/documents.py`, `models/webhook.py`, etc.) and core services have 0% test coverage. | **High** | `untested_files_report.txt`, `backend/app/services/` | Test Coverage | 24 hrs (3 SP) |
| **TD-023** | System Documentation Drift | `AGENTS.md` and `API_REFERENCE.md` document non-existent files (`api/routes.py`) and invalid endpoint paths. | **High** | `AGENTS.md:12-18`, `API_REFERENCE.md:39` | Documentation | 6 hrs (0.75 SP) |
| **TD-024** | Empty `.secrets.baseline` Scan Config | `.secrets.baseline` contains `"results": {}` with no custom regex rules for NVIDIA or Groq API keys. | **Low** | `.secrets.baseline:1-9` | Security CI | 2 hrs (0.25 SP) |
| **TD-025** | Vitest Thread Isolation State Leak | 17 frontend Vitest test files leak module state and fail during full runs unless passed `--pool=fork`. | **Medium** | `frontend/package.json`, `vitest.config.js` | Test Isolation | 2 hrs (0.25 SP) |

---

## 2. Enterprise Risk Register

The Enterprise Risk Register categorizes system risks into five critical operational domains: Security, Data Loss, Availability & Performance, Maintainability & Architecture, and Community & Onboarding.

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      ENTERPRISE RISK REGISTER                          │
 ├───────────────────┬───────────────────┬────────────────────────────────┤
 │ Risk Category     │ Highest Severity  │ Primary Technical Trigger      │
 ├───────────────────┼───────────────────┼────────────────────────────────┤
 │ Security          │ High              │ Docker non-root permission     │
 │ Data Loss         │ Critical          │ Sanitization newline stripping │
 │ Availability      │ Critical          │ DB generator connection leak   │
 │ Maintainability   │ High              │ Monolithic documents_impl.py   │
 │ Community/Onboard │ High              │ Documentation path drift       │
 └───────────────────┴───────────────────┴────────────────────────────────┘
```

### 2.1 Security Risks

- **RISK-SEC-01: Container Runtime Privilege Crash (Severity: High | Likelihood: High)**
  - *Description:* `backend/Dockerfile` copies dependencies from `/root/.local` to stage 2, then executes as `USER amf`. Unprivileged non-root users cannot read `/root/.local` in strict OCI environments (Cloud Run, EKS), causing container crash loop on launch.
  - *Remediation:* Update `Dockerfile` to copy to `/home/amf/.local` with `--chown=amf:amf`.
- **RISK-SEC-02: Silent Prompt Injection Guard Replacement Truncation (Severity: Medium | Likelihood: Medium)**
  - *Description:* Re-entrant regex pattern replacement in `llm_provider_service.py` replaces injection attempts with `[CONTENT_FILTERED]`. String boundary shifts during multi-pass replacement can unexpectedly truncate document text without recording security audit logs.
  - *Remediation:* Enforce single-pass tokenization filtering and record security violation audit logs in Supabase.
- **RISK-SEC-03: Empty Secret Baseline Scanner (Severity: Low | Likelihood: Medium)**
  - *Description:* `.secrets.baseline` contains empty results, allowing accidental commit of NVIDIA (`nvapi-`) or Groq API keys if developer pre-commit configuration is incomplete.
  - *Remediation:* Audit secret baseline using `detect-secrets scan` and configure custom regex match rules for LLM provider key formats.

---

### 2.2 Data Loss & Content Corruption Risks

- **RISK-DATA-01: Manuscript Line-Break Stripping via Payload Sanitization (Severity: Critical | Likelihood: High)**
  - *Description:* `removeControlChars` in `frontend/src/services/api.core.js` filters characters with ASCII code `< 32`. Newlines (`\n`), carriage returns (`\r`), and tabs (`\t`) are stripped. User manuscript text sent through `sanitizePayload` has all paragraph breaks flattened into a single unformatted line prior to server processing.
  - *Remediation:* Amend `removeControlChars` filter to retain ASCII 10, 13, and 9.
- **RISK-DATA-02: Storage Exhaustion via Vector Store TTL Loss (Severity: Medium | Likelihood: High)**
  - *Description:* Session vector store TTL deletion relies on in-memory timers (`threading.Timer`). Backend container restarts drop active timer instances, leaving ChromaDB vector store collections on disk permanently.
  - *Remediation:* Implement persistent TTL session tracking in Redis or a scheduled background cleanup job.

---

### 2.3 Availability, Stability & Performance Risks

- **RISK-AVAIL-01: Database Connection Pool Exhaustion via Generator Misuse (Severity: Critical | Likelihood: High)**
  - *Description:* `next(get_db())` invoked in `llm_fallback_service.py` and `llm_key_service.py` advances the SQLAlchemy session generator without calling `.close()`, bypassing `finally: db.close()`. High traffic leads to rapid connection pool exhaustion and HTTP 500 errors.
  - *Remediation:* Replace `next(get_db())` with `with SessionLocal() as db:` context managers.
- **RISK-AVAIL-02: Async Event Loop Thread Blocking (Severity: High | Likelihood: Medium)**
  - *Description:* Synchronous CPU/IO tasks (`python-docx` file generation, `difflib.HtmlDiff`) execute directly inside `async def` endpoints (`format_manuscript`, `get_comparison_data`), blocking the main event loop thread and causing latency spikes across all concurrent requests.
  - *Remediation:* Offload CPU-heavy synchronous calls using `await asyncio.to_thread(...)`.
- **RISK-AVAIL-03: Pytest Collection Timeout in CI Pipelines (Severity: High | Likelihood: High)**
  - *Description:* Router lazy-loader initialization loop causes `pytest tests/` collection to take >600 seconds, causing CI build jobs to timeout and fail.
  - *Remediation:* Refactor router discovery in `main.py` and add session-scoped pytest router pre-loading fixtures.

---

### 2.4 Maintainability & Clean Architecture Risks

- **RISK-MAINT-01: Domain Coupling in Monolithic Router Implementation (Severity: High | Likelihood: High)**
  - *Description:* `documents_impl.py` (1,350 lines) directly performs virus scanning, file hashing, magic byte checking, Redis caching, database updates, and export compilation, preventing clean service reusability.
  - *Remediation:* Decompose `documents_impl.py` into application services (`DocumentPipelineService`, `DocumentCrudService`, `DocumentExportService`).
- **RISK-MAINT-02: Frontend App Router Fragmentation (Severity: High | Likelihood: High)**
  - *Description:* The codebase contains two App Router trees (`frontend/app` vs `frontend/src/app`). `tsconfig.json` excludes `src/app`, resulting in dead code and developer confusion.
  - *Remediation:* Consolidate routing into `frontend/app/`, convert pages to TypeScript `.tsx`, and clean up `src/app`.

---

### 2.5 Community Onboarding & Developer Experience Risks

- **RISK-COMM-01: Documentation Path & Route Mismatches (Severity: High | Likelihood: High)**
  - *Description:* `AGENTS.md` and `API_REFERENCE.md` document invalid file paths (`api/routes.py`, `api/models.py`) and legacy routes (`POST /api/v1/format`), causing AI coding agents and external developers to generate incompatible code.
  - *Remediation:* Synchronize `AGENTS.md`, `API_REFERENCE.md`, and `ERROR_CODES.md` with active FastAPI implementations.
- **RISK-COMM-02: Missing Environment Variable Documentation (Severity: Medium | Likelihood: High)**
  - *Description:* `.env.example` omits LLM provider API keys (`NVIDIA_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY`), hindering new developer setup.
  - *Remediation:* Update `.env.example` with documented configuration keys for all supported AI providers.

---

## Technical Debt Risk Summary Matrix

```
       HIGH  │ [RISK-DATA-01]  [RISK-AVAIL-01] [RISK-SEC-01]
             │ [RISK-COMM-01]  [RISK-MAINT-01] [RISK-AVAIL-03]
  LIKELIHOOD │
       MED   │ [RISK-SEC-02]   [RISK-DATA-02]  [RISK-AVAIL-02]
             │ [RISK-COMM-02]  [RISK-SEC-03]
             └─────────────────────────────────────────────────
                     LOW             MED             HIGH
                                  SEVERITY
```
