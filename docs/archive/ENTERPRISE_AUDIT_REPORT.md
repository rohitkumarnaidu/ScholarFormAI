# ScholarFormAI Enterprise System Audit & Technical Analysis Report

**Date:** July 2026  
**Auditor:** Synthesis Engineering Team (`worker_synthesis`)  
**Scope:** Complete ScholarFormAI Monorepo (`backend/`, `frontend/`, `cli/`, `sdk/`, `deploy/`, `.github/`, `docs/`, `graphify-out/`)

---

## Executive Summary & Findings Matrix

A forensic, multi-domain system audit was conducted across the ScholarFormAI codebase, synthesizing findings from four specialized exploration agents (Backend & Services, Frontend UI & Client, CLI/SDK/Infra/AI, System Architecture & Verification).

ScholarFormAI features sophisticated multi-tier pipeline orchestration, automated citation engine formatting, RAG vector retrieval, and extensive GitHub Actions CI/CD workflows. However, the system suffers from **critical runtime bugs, data loss defects, container security failures, clean architecture violations, test suite collection bottlenecks, documentation drift, and unverified certification claims**.

### Synthesis Findings Matrix

| ID | Domain | Area / Component | Severity | Primary Defect / Issue | Location |
| --- | --- | --- | --- | --- | --- |
| **CRIT-01** | Backend | API / Routing | **Critical** | Core routes (`/format`, `/validate`, `/preview`, `/styles`) in `app/api/routes.py` are unmounted in `main.py` | `backend/app/main.py:262-274`, `backend/app/api/routes.py:31-97` |
| **CRIT-02** | Backend | Database / Services | **Critical** | DB connection leak via generator dependency `next(get_db())` suspended without cleanup | `backend/app/services/llm_fallback_service.py:207`, `llm_key_service.py:64` |
| **CRIT-03** | Frontend | Services / Data Loss | **Critical** | Text sanitization `removeControlChars` filters ASCII `< 32`, silently stripping all `\n`, `\r`, `\t` from manuscripts | `frontend/src/services/api.core.js:48-55` |
| **CRIT-04** | SDK | Client Runtime | **Critical** | SDK `AMFError` exception is not imported in `client.py:62`, causing fatal `NameError` on HTTP 500/502 errors | `sdk/amf_sdk/client.py:62` |
| **CRIT-05** | Testing | Test Suite / Coverage | **Critical** | `--cov` coverage tracing crashes pytest with `KeyError: 'pydantic.root_model'`, obscuring real coverage metrics | `backend/pytest.ini`, `COVERAGE_GAP_REPORT.md` |
| **HIGH-01** | Backend | Clean Architecture | **High** | God class `ManuscriptFormatter` (9 responsibilities) & 1,350-line procedural file `documents_impl.py` | `backend/app/services/formatter.py:17-357`, `backend/app/routers/v1/documents_impl.py` |
| **HIGH-02** | Backend | Service / API Coupling | **High** | Business services (`formatter.py`, `parser.py`, `validator.py`) directly import Pydantic HTTP API models | `backend/app/services/formatter.py:11`, `parser.py:4`, `validator.py:4` |
| **HIGH-03** | Frontend | Architecture | **High** | Dual App Router: Active `.jsx` router in `app/` vs orphaned `.tsx` router in `src/app/` excluded in `tsconfig.json` | `frontend/src/app/`, `frontend/tsconfig.json:51` |
| **HIGH-04** | Frontend | Type Safety & Linting | **High** | ESLint targets only `.js,.jsx`, `@typescript-eslint` is absent, and React Hooks rules are explicitly disabled | `frontend/package.json:13`, `frontend/eslint.config.js:18-25` |
| **HIGH-05** | Infra | Container Security | **High** | Dockerfile copies `/root/.local` to non-root user `amf`, causing `Permission Denied` startup crash | `backend/Dockerfile:13-25` |
| **HIGH-06** | Testing | Test Collection | **High** | Router cold-boot loader causes `pytest tests/` test collection to exceed 600s timeout | `backend/app/main.py:687-695`, `TECHNICAL_DEBT.md:TD-021` |
| **HIGH-07** | Docs | Documentation Drift | **High** | `AGENTS.md` and `API_REFERENCE.md` reference non-existent files (`api/routes.py`, `api/models.py`) and legacy routes | `AGENTS.md:12-18`, `API_REFERENCE.md:39` |
| **HIGH-08** | Testing | Test Coverage | **High** | 8 backend modules completely untested & 0% unit test coverage for core business services | `untested_files_report.txt`, `backend/app/services/` |
| **MED-01** | Backend | Storage / API | **Medium** | Temporary `.docx` files created in `/format` with `delete=False` are never unlinked | `backend/app/api/routes.py:39-43` |
| **MED-02** | Backend | Async Performance | **Medium** | Heavy synchronous CPU/IO (OpenXML building, `difflib.HtmlDiff`) executed directly in `async def` routes | `backend/app/api/routes.py:32`, `backend/app/routers/v1/documents_impl.py:988` |
| **MED-03** | Backend | Database Architecture | **Medium** | Architecture duality: Supabase REST client (`supabase-py`) vs SQLAlchemy ORM engine (`session.py`) | `backend/app/db/supabase_client.py`, `backend/app/db/session.py` |
| **MED-04** | Frontend | API Service Layer | **Medium** | Dual API service layers: Strongly typed `src/lib/api.ts` is ignored in favor of 19 untyped `src/services/*.js` | `frontend/src/lib/api.ts`, `frontend/src/services/` |
| **MED-05** | Frontend | Accessibility / UX | **Medium** | HTML nesting spec violation (`<button>` inside `<div role="button">`) & Material Symbols font dependency | `frontend/src/components/FileUpload.jsx:74-119` |
| **MED-06** | Frontend | Constants Alignment | **Medium** | Citation style constants in `constants.ts` mismatch backend internal IDs in `style_registry.py` | `frontend/src/lib/constants.ts:1-11`, `style_registry.py:46-240` |
| **MED-07** | CLI | Performance | **Medium** | Watch mode in CLI `format.py` uses `while True: time.sleep(1)` busy polling instead of file system events | `cli/amf/commands/format.py:68-74` |
| **MED-08** | AI/RAG | Operations / Storage | **Medium** | ChromaDB vector store TTL timers managed via in-memory `threading.Timer` / `create_task`, lost on restart | `backend/app/services/session_vector_store.py:117-131` |
| **MED-09** | AI/RAG | Security Guardrails | **Medium** | Re-entrant pattern replacement in LLM prompt injection guard may unpredictably truncate input text | `backend/app/services/llm_provider_service.py:187-195` |
| **MED-10** | Testing | Frontend Test Suite | **Medium** | 17 Vitest test files leak module state and fail during full runs unless executed with `--pool=fork` | `frontend/package.json`, `vitest.config.js` |
| **LOW-01** | Backend | Code Hygiene | **Low** | Deprecated `datetime.utcnow` used in Pydantic schema default factories | `backend/app/api/models.py:95, 143` |
| **LOW-02** | Infra | Security / CI | **Low** | `.secrets.baseline` is empty (`"results": {}`), skipping key scanning for NVIDIA and Groq formats | `.secrets.baseline:1-9` |

---

## 1. Backend Architecture, Routing & Services Audit

### 1.1 Unmounted Core API Routes (`CRIT-01`)

- **Location:** `backend/app/main.py:262-274`, `backend/app/api/routes.py:31-97`
- **Analysis:** `app/main.py` defines `_load_optional_routers()` which mounts `v1_router` (`app.routers.v1`) and `preview.router` (`app.routers.preview`). However, `app/api/routes.py` (containing endpoints `@router.post("/format")`, `@router.post("/validate")`, `@router.post("/preview")`, `@router.get("/styles")`) is **never included** in `app`.
- **Impact:** Requests to `/format` or `/styles` as documented in legacy guides return HTTP 404. Furthermore, line 53 of `routes.py` generates `download_url=f"/api/v1/download/{filename}"`, which does not exist in the active router (active route is `/api/v1/documents/{jobId}/download`).

### 1.2 DB Connection Leak via Generator Misuse (`CRIT-02`)

- **Location:** `backend/app/services/llm_fallback_service.py:207`, `backend/app/services/llm_key_service.py:64`
- **Analysis:** Code invokes `db: Session = next(get_db())` to obtain a database session inside non-FastAPI dependency service contexts.
- **Impact:** `get_db()` is a generator function (`try: yield db finally: db.close()`). Calling `next()` advances the generator to the `yield` statement, but because a second `next()` or `.close()` is never executed, the `finally: db.close()` block **never runs**. Under multi-threaded request processing, connections in the SQLAlchemy connection pool leak continuously until the pool is exhausted.

### 1.3 God Class & Procedural Overcrowding (`HIGH-01`)

- **Location:** `backend/app/services/formatter.py:17-357`, `backend/app/routers/v1/documents_impl.py`
- **Analysis:**
  1. `ManuscriptFormatter` in `formatter.py` violates SRP by combining margin setup, font configuration, title page rendering, running header insertion, abstract/keyword handling, section body parsing, CSL citation string generation, OpenXML page numbering, page count estimation, and HTML preview generation into a single class.
  2. `documents_impl.py` is a 1,350-line procedural file that handles HTTP validation, virus scanning (`_scan_uploaded_file`), magic byte checking, Redis status caching, direct file system deletion, Supabase database calls, and direct `PipelineOrchestrator` / `LaTeXExporter` / `PDFExporter` instantiation.
- **Impact:** Tight coupling prevents reusing core parsing and export logic across CLI, SDK, or background workers without re-implementing router-level glue code.

### 1.4 Business Service Coupling to HTTP Pydantic Models (`HIGH-02`)

- **Location:** `backend/app/services/formatter.py:11`, `parser.py:4`, `validator.py:4`
- **Analysis:** Core domain services directly import Pydantic models (`Manuscript`, `FormattingOptions`, `Section`, `Author`, `Reference`) from `app.api.models`.
- **Impact:** Violates the Dependency Inversion Principle (DIP). Core business logic cannot evolve independently of the HTTP presentation schema contract.

### 1.5 Resource Leaks & Async Event Loop Blocking (`MED-01`, `MED-02`)

- **Temporary File Leak:** `routes.py:39-43` uses `NamedTemporaryFile(suffix=".docx", delete=False)` without a cleanup handler, leaving temporary files on disk after returning HTTP responses.
- **Event Loop Blocking:** `async def format_manuscript` and `async def get_comparison_data` perform CPU-bound OpenXML building and heavy string diffing (`difflib.HtmlDiff().make_file(...)`) directly on the asyncio event loop thread, causing request latency spikes for concurrent users.

---

## 2. Frontend UI, App Router & Client Architecture Audit

### 2.1 Text Sanitization Newline Stripping Data Loss Bug (`CRIT-03`)

- **Location:** `frontend/src/services/api.core.js:48-55`
- **Analysis:** `removeControlChars` sanitizes string payloads before API submission by filtering characters:

  ```javascript
  const removeControlChars = (input) => (
      Array.from(String(input ?? ''))
          .filter((char) => {
              const code = char.charCodeAt(0);
              return code >= 32 && code !== 127;
          })
          .join('')
  );
  ```

- **Impact:** ASCII 10 (`\n`), ASCII 13 (`\r`), and ASCII 9 (`\t`) are all `< 32`. Any multiline manuscript text or structured input processed by `sanitizePayload` has **all line breaks silently removed**, collapsing multiline academic papers into a single unformatted block of text prior to server transmission.

### 2.2 Dual App Router Structure & Dead Code (`HIGH-03`)

- **Location:** `frontend/app/` vs `frontend/src/app/`, `frontend/tsconfig.json:51`
- **Analysis:** The repository contains two parallel Next.js App Router directory trees:
  1. Active Router: `frontend/app/` written in JavaScript (`.jsx`).
  2. Inactive Router: `frontend/src/app/` written in TypeScript (`.tsx`).
  `tsconfig.json` explicitly excludes `"src/app"` from TypeScript compilation.
- **Impact:** Developers updating files in `frontend/src/app/` are editing dead code that is completely ignored by Next.js and the TypeScript compiler.

### 2.3 Type Safety & Linting Bypass (`HIGH-04`)

- **Location:** `frontend/package.json:13`, `frontend/eslint.config.js:18-25`
- **Analysis:** `package.json` lint command is hardcoded to target only JavaScript files: `"lint": "eslint . --ext js,jsx"`. `@typescript-eslint` is absent. Furthermore, `eslint.config.js` explicitly disables core React Hooks rules:

  ```javascript
  "react-hooks/set-state-in-effect": "off",
  "react-hooks/refs": "off",
  "react-hooks/purity": "off",
  "react-hooks/immutability": "off",
  ```

- **Impact:** All TypeScript source files in `frontend/src/` (`.ts`, `.tsx`) are completely bypassed by linting, and critical React state mutation anti-patterns pass without warnings.

### 2.4 Dual API Service Layers & Icon Font Vulnerabilities (`MED-04`, `MED-05`, `MED-06`)

- **Dual API Clients:** Strongly-typed API interfaces in `frontend/src/lib/api.ts` are ignored by UI components in favor of 19 untyped JavaScript modules in `frontend/src/services/`.
- **HTML Nesting & Icons:** `FileUpload.jsx` renders `<button>` inside `<div role="button">`, causing invalid HTML nesting and duplicate click handler invocations. Icon components rely on Google Material Symbols font tags (`<span className="material-symbols-outlined">...</span>`), which render as raw text strings ("cloud_upload") in air-gapped environments.
- **Constant Mismatch:** `constants.ts` defines `citation_format` as `'Author-Year'` or `'Numbered'`, whereas `backend/app/services/style_registry.py` returns internal style codes (`'apa'`, `'ieee'`).

---

## 3. CLI, SDK, AI/RAG Services & Infrastructure Audit

### 3.1 SDK Fatal `NameError` Bug (`CRIT-04`)

- **Location:** `sdk/amf_sdk/client.py:62`
- **Analysis:** `_handle_response` maps HTTP error codes:

  ```python
  error_map.get(response.status_code, AMFError)
  ```

  However, `AMFError` is **not imported** anywhere in `client.py:7-15` (only specific subclasses like `ValidationError`, `AuthenticationError`, `NotFoundError` are imported).
- **Impact:** Receiving any unmapped HTTP error code (e.g. HTTP 500 Internal Server Error or HTTP 502 Bad Gateway) causes the SDK to throw `NameError: name 'AMFError' is not defined` instead of raising an SDK exception.

### 3.2 Docker Container Permission Crash (`HIGH-05`)

- **Location:** `backend/Dockerfile:13-25`
- **Analysis:** The multi-stage `Dockerfile` copies builder dependencies to `/root/.local`:

  ```dockerfile
  COPY --from=builder /root/.local /root/.local
  USER amf
  ```

- **Impact:** The unprivileged non-root user `amf` lacks read and execute permissions to access files inside `/root/`. Deploying this image to strict OCI runtimes (GCP Cloud Run, AWS Fargate, Kubernetes) causes immediate container crash on startup (`Permission denied`).

### 3.3 RAG Architecture & Vector Store Storage Leak (`MED-08`)

- **Location:** `backend/app/services/session_vector_store.py:117-131`
- **Analysis:** `_schedule_ttl_delete` schedules deletion of ephemeral session vector stores using in-memory `threading.Timer` or `asyncio.create_task`.
- **Impact:** If the FastAPI backend process restarts or scales down, active timers in memory are lost. The corresponding ChromaDB vector collections remain on disk indefinitely, creating a storage leak.

### 3.4 CLI Busy Polling (`MED-07`)

- **Location:** `cli/amf/commands/format.py:68-74`
- **Analysis:** `_format_and_watch()` implements watch mode via a `while True: time.sleep(1)` loop checking `os.stat().st_mtime`.
- **Impact:** Causes continuous CPU wakeups and disk polling overhead instead of utilizing native OS file system event hooks (`watchdog`).

---

## 4. System Architecture, Graphify Knowledge Graph & Coupling Analysis

### 4.1 Knowledge Graph Topological Overview

Analysis of `graphify-out/GRAPH_REPORT.md` and `graphify-out/graph.json` reveals the structural topology of ScholarFormAI:

- **Total Graph Nodes:** 233 | **Total Directed Edges:** 81 | **Total Communities:** 169
- **God Nodes (Central Hubs):**
  1. `PipelineOrchestrator` (23 edges): Central hub connecting parsing, reasoning, template formatting, citation assembly, and export rendering.
  2. `FastAPI` (16 edges): Central gateway enforcing JWT verification, rate limiting, and routing.
  3. `ParserFactory` (8 edges): Dispatcher for multi-format text extraction.
  4. `LiteLLM` (8 edges): Central AI provider multiplexer.
  5. `RagEngine` & `RedisPubSub` (5 edges each).

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      FastAPI Gateway                        │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                 PipelineOrchestrator                        │ ◄── (God Node: 23 Edges)
 └───────┬──────────────────────┬──────────────────────┬───────┘
         │                      │                      │
 ┌───────▼────────┐     ┌───────▼────────┐     ┌───────▼────────┐
 │ ParserFactory  │     │ FormatterEngine│     │ RagEngine/LLM  │
 └────────────────┘     └────────────────┘     └────────────────┘
```

### 4.2 Community Fragmentation & Test Collection Bottlenecks (`HIGH-06`)

- **Modularity Fragmentation:** 160 out of 169 identified communities contain fewer than 3 nodes, and **211 nodes are isolated** without explicit interface connections.
- **Router Cold-Boot Bottleneck:** To avoid a ~15-second per-router startup penalty, `backend/app/main.py` uses `lazy_router_loader`. However, during `pytest tests/` test suite collection, router dependencies are evaluated sequentially, causing test collection to exceed 600-second timeouts (`TECHNICAL_DEBT.md:TD-021`).

---

## 5. Test Suite & Verification Reality Audit

### 5.1 Broken Coverage Measurement (`CRIT-05`)

- **Location:** `backend/pytest.ini`, `COVERAGE_GAP_REPORT.md`, `TECHNICAL_DEBT.md:TD-003`
- **Analysis:** Running `pytest --cov=app` fails with:

  ```
  KeyError: 'pydantic.root_model'
  ```

  This occurs due to a collision during coverage tracing of Pydantic v2.13+ RootModel definitions.
- **Impact:** Automated CI coverage gates cannot measure line coverage accurately. Claims of "100% coverage" in `ENTERPRISE_CERTIFICATION.md` are unverified.

### 5.2 Untested Backend Modules Audit (`HIGH-08`)

`untested_files_report.txt` verifies that **8 backend modules** are completely missing unit test coverage:

1. `backend/app/db/base.py`: Database metadata initialization uncovered.
2. `backend/app/models/suggestion.py`: AI suggestion entity serialization uncovered.
3. `backend/app/models/webhook.py`: Webhook subscription model uncovered.
4. `backend/app/routers/v1/activity.py`: User activity stream router uncovered.
5. `backend/app/routers/v2/documents.py`: Next-gen v2 document router completely untested.
6. `backend/app/routers/v2/webhooks.py`: v2 Webhook management endpoints completely untested.
7. `backend/app/schemas/pagination.py`: Pagination envelope schema uncovered.
8. `backend/app/schemas/webhook.py`: Webhook payload validation schema uncovered.

Furthermore, **0% unit test coverage** exists for legacy core business services (`formatter.py`, `parser.py`, `validator.py`, `style_registry.py`).

### 5.3 Vitest Thread Isolation Failures (`MED-10`)

Running the frontend unit test suite without explicit process isolation causes **17 Vitest test files** to fail due to unisolated module-level mock state leaks. Test execution requires passing `--pool=fork`.

---

## 6. Documentation Drift & Open-Source Readiness Audit

### 6.1 Documentation Discrepancies (`HIGH-07`)

1. **`AGENTS.md` Path Inaccuracies:**
   - Refers to repository name as `automated-manuscript-formatter/` instead of `ScholarFormAI`.
   - References non-existent file paths `backend/app/api/routes.py` and `backend/app/api/models.py` (active routes reside in `backend/app/routers/v1/documents.py`).
2. **`API_REFERENCE.md` Outdated Routes:**
   - Documents legacy endpoints `POST /api/v1/format`, `POST /api/v1/validate`, and `GET /api/v1/styles`.
   - Actual implemented endpoints are `POST /api/v1/documents/upload` and `GET /api/v1/templates/`.
3. **`ERROR_CODES.md` Envelope Mismatch:**
   - Documents legacy error codes (`MISSING_TITLE`, `MISSING_AUTHORS`) that are not returned by FastAPI standardized error envelopes (`INVALID_UPLOAD_REQUEST`, `DOCUMENT_VALIDATION_FAILED`).
4. **`RAG.md` & `AI.md` Status Mismatch:**
   - `RAG.md` states vector retrieval is in "planning stage for v2.0", while backend code contains a complete LiteLLM + ChromaDB implementation in `session_vector_store.py`.

### 6.2 Dead Code & Stale Artifacts

- Obsolete fix script `backend/scripts/fix_all_broken_pipeline_tests.py` remains in source tree.
- Legacy Vite build directory `frontend/dist/` remains committed.
- Empty documentation directories `docs/proposal/` and `docs/images/`.
- Missing SPDX license headers in several `cli/` and `sdk/` source files.

---

## Conclusion & Strategic Recommendations

ScholarFormAI has a powerful feature set, but requires a structured 4-phase refactoring initiative to resolve critical defects, establish true clean architecture, ensure 100% test verification, and align documentation with implementation.
