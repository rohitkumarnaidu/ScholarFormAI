# ScholarFormAI Before vs. After Architecture Comparison & Developer Migration Guide

**Date:** July 2026  
**Author:** Synthesis Engineering Team (`worker_synthesis`)  
**Target:** ScholarFormAI Monorepo (`backend/`, `frontend/`, `cli/`, `sdk/`, `deploy/`, `docs/`)

---

## Executive Overview

This document presents a detailed comparison of ScholarFormAI's architecture **Before** (current state) versus **After** (post-refactoring state across all 4 refactoring phases). It includes a step-by-step developer migration guide covering API breaking changes, local environment setup, SDK/CLI upgrading instructions, and open-source contributor onboarding workflows.

---

## 1. Before vs. After Architecture Comparison Matrix

| Architectural Component | BEFORE (Legacy State) | AFTER (Refactored Target State) | Strategic Benefit |
|---|---|---|---|
| **Backend API Routing** | Core endpoints (`/format`, `/validate`) unmounted in `main.py` & orphaned in `api/routes.py`. Download path URL mismatched. | Unmounted routes removed/refactored into active v1 router under `/api/v1/documents/upload`. Downloads return signed URLs. | 100% route mounting, zero orphaned endpoint code, predictable HTTP responses. |
| **Database Session Management** | `next(get_db())` invoked in service layers, suspending generators without calling `finally: db.close()`. | All non-dependency services use `with SessionLocal() as db:` context managers. | Zero database connection leaks, stable connection pool under load. |
| **Document Processing Monolith** | 1,350-line procedural file `documents_impl.py` handles HTTP, virus scanning, magic bytes, Redis status, DB, and exporters. | Decomposed into application services (`DocumentPipelineService`, `DocumentCrudService`, `DocumentExportService`). | Clean Architecture compliance, independent unit testability, domain reusability. |
| **Business Logic & God Classes** | `ManuscriptFormatter` class manages 9 separate layout, OpenXML, CSL, estimation, and HTML preview responsibilities. | Decomposed into `DocumentLayoutEngine`, `ReferenceRenderer`, `PageEstimator`, `HTMLPreviewRenderer`. | Adherence to Single Responsibility Principle (SRP); isolated modification boundaries. |
| **Domain Model Dependency** | Business services (`formatter.py`, `parser.py`, `validator.py`) directly import HTTP Pydantic models from `app.api.models`. | Core business services operate exclusively on domain dataclasses (`app/domain/models.py`). | Adherence to Dependency Inversion Principle (DIP); decoupling domain from HTTP presentation. |
| **Async Execution Performance** | Heavy synchronous CPU/IO (`python-docx` file generation, `difflib.HtmlDiff`) runs directly on asyncio event loop thread. | CPU-heavy synchronous calls wrapped in `await asyncio.to_thread(...)`. | Prevents event loop blocking; reduces p99 request latency for concurrent users. |
| **Frontend App Router** | Dual App Router trees: Active JS `.jsx` router in `app/` vs orphaned TS `.tsx` router in `src/app/` (excluded in `tsconfig.json`). | Consolidated single App Router in `frontend/app/` using TypeScript `.tsx` throughout. | Eliminates dead code, provides compile-time page verification. |
| **Frontend API Service Layer** | Strongly typed `src/lib/api.ts` ignored in favor of 19 untyped JavaScript modules in `src/services/`. | 19 untyped JS services deprecated; UI components standardized on strongly-typed `src/lib/api.ts`. | End-to-end TypeScript API response safety, single network client interface. |
| **Text Sanitization & Data Integrity** | `removeControlChars` filters ASCII `< 32`, silently stripping all `\n`, `\r`, `\t` from uploaded manuscripts. | `removeControlChars` amended to explicitly preserve ASCII 10 (`\n`), 13 (`\r`), and 9 (`\t`). | Zero text corruption; preserves manuscript multiline structure during formatting. |
| **Frontend Type Safety & Linting** | ESLint targets only `.js,.jsx`, `@typescript-eslint` is absent, and React Hooks rules are explicitly disabled. | ESLint configured for `.ts,.tsx`, `@typescript-eslint` enabled, React Hooks rules enforced. | Automated detection of React state mutations, closure bugs, and type errors. |
| **Frontend UI Components & Icons** | `<button>` inside `<div role="button">` in `FileUpload.jsx`; Google Material Symbols font tags used for icons. | Valid HTML element nesting; Material Symbols font tags replaced with native `lucide-react` SVG components. | Full WCAG 2.2 AA accessibility compliance, reliable offline icon rendering. |
| **Python SDK Error Resilience** | SDK `AMFError` exception unimported in `client.py:62`, causing fatal `NameError` on HTTP 500/502 responses. | `AMFError` imported cleanly; automated retry middleware with exponential backoff added to `httpx`. | Graceful exception handling in SDK clients, resilience against transient server errors. |
| **Container Security & Privileges** | Dockerfile copies `/root/.local` to non-root user `amf`, causing `Permission Denied` crash on strict OCI runtimes. | Dockerfile copies to `/home/amf/.local` with `--chown=amf:amf` execution privileges. | OCI compliant container deployment on GCP Cloud Run, AWS Fargate, and Kubernetes. |
| **Vector Store TTL Persistence** | Vector store collection cleanup managed via volatile in-memory `threading.Timer`, lost on process restart. | TTL session cleanup persisted in Redis TTL keys and scheduled Celery cleanup tasks. | Eliminates ChromaDB disk storage leaks across server restarts. |
| **Test Suite Infrastructure** | `--cov` fails with `pydantic.root_model` KeyError; router cold-boot loader causes >600s pytest collection timeout. | `--cov` configured cleanly in `.coveragerc`; router discovery optimized (< 15s collection time). | Fast local and CI test runs, accurate line and branch coverage measurement. |
| **Untested Backend Modules** | 8 backend files and core business services have 0% unit test coverage. | 100% module coverage with dedicated unit test suites for all 8 files and core services. | Verifiable code quality, zero untested backend source files. |
| **System Documentation** | `AGENTS.md` and `API_REFERENCE.md` reference non-existent files (`api/routes.py`) and legacy routes (`/format`). | System documentation synchronized with implementation, route endpoints, and file paths. | Smooth developer onboarding, accurate AI coding agent assistance. |

---

## 2. Step-by-Step Developer Migration Guide

This section outlines breaking changes and migration steps required for developers, SDK consumers, and system operators updating to the refactored ScholarFormAI architecture.

### 2.1 API Contract Breaking Changes & Migration

#### 1. Endpoint Path Standardization
- **OLD Route:** `POST /format` or `POST /api/v1/format`
- **NEW Route:** `POST /api/v1/documents/upload`
- **Migration Action:** Update HTTP API requests to target `/api/v1/documents/upload` with `multipart/form-data` payload containing `file`, `target_style`, and optional options JSON.

#### 2. Template Response Envelope Wrapping
- **OLD Response (`GET /api/v1/styles`):** Returned raw JSON array `[ { "id": "apa", ... }, ... ]`.
- **NEW Response (`GET /api/v1/templates/`):** Returns enveloped JSON object:
  ```json
  {
    "templates": [
      {
        "id": "apa",
        "name": "APA 7th Edition",
        "citation_format": "apa"
      }
    ],
    "total": 1
  }
  ```
- **Migration Action:** Update client parsing logic to extract `response.data.templates` instead of expecting a top-level array.

#### 3. Download URL Path Resolution
- **OLD Response Field:** `download_url: "/api/v1/download/document.docx"` (Returned 404).
- **NEW Response Field:** `download_url: "/api/v1/documents/job_12345/download"`
- **Migration Action:** Use `download_url` directly as returned by the status API; signed tokens are automatically appended when requested.

---

### 2.2 Local Developer Setup & Environment Migration

#### Step 1: Python Environment & Dependency Setup
Ensure Python 3.12+ is active and install refreshed dependencies:
```powershell
# Navigate to backend directory
cd backend

# Create virtual environment if not present
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install backend in editable mode
python -m pip install --upgrade pip
pip install -e .[dev]
```

#### Step 2: Environment Variable Configuration
Copy `.env.example` to `.env` and configure required LLM provider keys:
```env
# Server Configuration
PORT=8000
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/scholarform
SUPABASE_URL=https://your-supabase-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key

# LLM & AI Provider Keys
NVIDIA_API_KEY=nvapi-your-nvidia-key
GROQ_API_KEY=gsk_your-groq-key
OPENROUTER_API_KEY=sk-or-your-openrouter-key
OLLAMA_BASE_URL=http://localhost:11434
```

#### Step 3: Frontend Environment Setup
Navigate to `frontend/` and update Node modules and ESLint plugins:
```powershell
cd ../frontend

# Install dependencies including lucide-react and @typescript-eslint
npm install

# Run linting across all JS and TS files
npm run lint

# Execute frontend unit test suite with isolated process forks
npm test
```

---

### 2.3 Python SDK & CLI Upgrade Guide

#### SDK Version 2.0 Migration
Install the updated SDK package:
```powershell
pip install -e sdk/
```

##### Synchronous Client Migration
```python
# BEFORE (v1.x):
from amf_sdk.client import AMFClient

client = AMFClient(base_url="http://localhost:8000")
# Unhandled NameError occurred if server returned HTTP 500

# AFTER (v2.0):
from amf_sdk.client import AMFClient
from amf_sdk.exceptions import AMFError, ServerError

with AMFClient(base_url="http://localhost:8000") as client:
    try:
        result = client.format_manuscript(
            file_path="manuscript.docx",
            style="apa"
        )
        print(f"Formatted document path: {result.download_url}")
    except ServerError as e:
        print(f"Server error handled cleanly: {e}")
    except AMFError as e:
        print(f"SDK base error caught: {e}")
```

##### Asynchronous Client Migration
```python
# NEW AsyncAMFClient Usage (v2.0):
import asyncio
from amf_sdk.async_client import AsyncAMFClient

async def main():
    async with AsyncAMFClient(base_url="http://localhost:8000") as client:
        status = await client.get_job_status(job_id="job_12345")
        print(f"Current status: {status.state}")

asyncio.run(main())
```

---

### 2.4 Open-Source Contributor Onboarding Workflow

To maintain high code quality standards, all new open-source contributions must follow this 5-step checklist:

1. **Check Repository Layout:** Ensure all backend source files reside under `backend/app/`, frontend files under `frontend/app/` or `frontend/src/`, and metadata under `.agents/`. (Never commit source code to `.agents/`).
2. **Include License Headers:** Ensure all newly created Python files include the standard SPDX header:
   ```python
   # SPDX-License-Identifier: MIT
   # Copyright (c. 2026 ScholarFormAI Contributors
   ```
3. **Run Pre-Commit Hooks:** Execute `pre-commit run --all-files` before submitting pull requests.
4. **Execute Verification Commands:**
   - Backend: `pytest --cov=app --cov-report=term-missing` (Must pass with 0 failures and >90% coverage).
   - Frontend: `npm test` and `npm run lint`.
5. **Verify System Documentation:** Update `API_REFERENCE.md` or `AGENTS.md` if adding or modifying API endpoints or service interfaces.
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Migration Guides

## Version 0.9 → 1.0

### Breaking Changes

#### Python version requirement
- **Old:** Python 3.11 (incompatible, caused pytest import collisions)
- **New:** Python 3.12.x required
- **Migration:** `pip install -r requirements.txt` under Python 3.12

#### Frontend framework
- **Old:** Vite (referenced in various docs)
- **New:** Next.js 16 App Router
- **Migration:** None needed — if you were using the frontend, it was already Next.js. Documentation has been corrected.

#### API routing
- **Old:** Some routes under `/api/v1/` were inconsistently versioned
- **New:** All routes now consistently under `/api/v1/` prefix
- **Migration:** Update any hardcoded `/api/documents/` references to `/api/v1/documents/`

#### Environment variables
- **Old:** `VITE_*` prefixed frontend env vars
- **New:** `NEXT_PUBLIC_*` prefixed frontend env vars
- **Migration:** Rename `VITE_API_URL` → `NEXT_PUBLIC_API_URL`

### Deprecations

- `api_reference.md` deprecated in favor of `API.md`
- `BACKUP_RESTORE.md` merged into `DISASTER_RECOVERY.md`
- `Spring Boot API gateway` plan item officially obsolete (ADR 004)

### New Features (0.9 → 1.0)

- 17 journal templates (up from 15)
- AI Agent generation pipeline (11-step)
- Multi-doc synthesis engine (ChromaDB RAG)
- Live preview WebSocket editor
- API key management with Fernet encryption
- Stripe billing integration
- 3-tier LLM fallback (NVIDIA NIM → Groq → Ollama)
- 3-tier PDF parser fallback (GROBID → Docling → PyMuPDF)

## Version 1.0 → 1.1 (Planned)

*(This section will be filled during the 1.1 release cycle.)*

## General Migration Tips

1. **Always back up your database** before upgrading: `pg_dump $SUPABASE_DB_URL --format=custom --file=pre-upgrade.dump`
2. **Read the CHANGELOG.md** for the full diff between versions
3. **Deploy to staging first** and run the full E2E test suite
4. **Update pinned dependencies** in `requirements.txt` and `package.json`
5. **Check for deprecation warnings** in API responses and server logs

---

*Last updated: July 2026*
