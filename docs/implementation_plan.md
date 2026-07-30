<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Implementation Plan
description: Agent-based implementation plan with task breakdown
sidebar_position: 71
version: "1.0"
status: 📋 Planned
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Implementation Plan

## Table of Contents

- [Critical Findings](#-critical-findings-combined-from-both-audits)
- [Phase 0: Restore Truth & Fast Feedback](#-phase-0-restore-truth--fast-feedback)
- [Phase 1: Canonical Documentation Reset](#phase-1-canonical-documentation-reset)
- [Phase 2: Contract & Smoke Validation](#phase-2-contract--smoke-validation)
- [Phase 3: Critical Gap Fixes](#phase-3-critical-gap-fixes)
- [Phase 4: Service-Backed Validation](#phase-4-service-backed-validation)
- [Phase 5: Launch Readiness](#phase-5-launch-readiness)
- [Additional Suggestions](#-my-additional-suggestions-not-in-any-audit)
- [Verification Plan](#verification-plan)

> **Sources combined:** Codex 5.4 audit (13 files), Antigravity audit (19 sections), Master Plan v4 DOCX (50 sections), 4 planning markdown files, user's original prompts
> **Agents:** Agent 1 (Backend/Infrastructure) + Agent 2 (Frontend/Docs)
> **Quality bar:** Don't miss a single item from any source

---

## 🚨 Critical Findings (Combined from Both Audits)

| # | Finding | Source |
| --- | --------- | -------- |
| 1 | **Python 3.11.9 local vs 3.12 required** — local env doesn't match repo contract | Codex |
| 2 | **pytest import collision** — `tests/conftest.py` imports `app.models` → resolves to third-party `app` package → crashes in `LLMPDFParser/albumentations` | Codex |
| 3 | **Frontend build fails** — `generate-tests.js:212` invalid template literal | Both |
| 4 | **Frontend vitest fails** — `@testing-library/dom` missing from devDependencies | Codex |
| 5 | **RBAC middleware is stub** (708B) | Antigravity |
| 6 | **Audit logging is stub** (1.1KB) | Antigravity |
| 7 | **api.synthesis.js is empty** (36B) | Antigravity |
| 8 | **latex_exporter.py is stub** (743B) | Antigravity |
| 9 | **globals.css is 117KB compiled Tailwind** — should not be committed | Antigravity |
| 10 | **Docs reference Vite/port 5173** — misleads contributors | Codex |
| 11 | **GROBID needs 1.5GB RAM** — can't run on Render free tier (512MB) | Antigravity |
| 12 | **No deploy-staging.yml** | Antigravity |
| 13 | **Planning docs are outdated** — many "TODO" items are already done | Codex |
| 14 | **34 page routes exist** but only ~25 are documented | Codex |

---

## Phase 0: Restore Truth & Fast Feedback (BLOCKER — Must be first)

> **Goal:** Get backend tests collecting and frontend build passing. Nothing else matters until this works.

### Agent 1 — Backend Stabilization

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 0.1 | **Recreate Python 3.12 environment** | Agent checks current Python version, creates new venv with Python 3.12, reinstalls requirements.txt | ️ **YES — Agent asks user:** "Do you have Python 3.12 installed? If not, please install it from python.org. Which path is your Python 3.12 executable?" | `python --version` returns 3.12.x in the backend venv |
| 0.2 | **Fix pytest import collision** | Agent inspects `tests/conftest.py`, identifies `app.models` import resolving to third-party `app` package. Fix: either (a) add `backend/` to sys.path in conftest, (b) restructure the import, or (c) uninstall conflicting `app` package | No | `pytest --collect-only -q` succeeds without LLMPDFParser/albumentations crash |
| 0.3 | **Fix LLMPDFParser/albumentations crash path** | After fixing import resolution, if crash persists, agent pins or patches the dependency. May need to add LLMPDFParser extras or fix version constraint | No | `pytest tests -m "not integration and not llm" -x -q` — collection succeeds |
| 0.4 | **Create `trusted-core` test profile** | Agent adds pytest markers in `pyproject.toml` or `pytest.ini`: `unit`, `integration`, `llm`, `service`. Ensures `pytest -m "not integration and not llm and not service"` only runs pure unit tests | No | Pure unit tests run without any external service |
| 0.5 | **Run and verify backend unit tests** | Agent runs `pytest tests -m "not integration and not llm" -x -q --tb=short` and fixes any failing tests | No | All unit tests pass (green) |

### Agent 2 — Frontend Stabilization

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 0.6 | **Fix generate-tests.js build error** | Agent fixes the template literal syntax at line 212. Options: (a) fix backtick escaping, (b) add to tsconfig exclude, (c) rename to .cjs | No | `npm run build` passes |
| 0.7 | **Add missing @testing-library/dom** | Agent runs `npm install --save-dev @testing-library/dom` | No | `npm test` — vitest base harness works |
| 0.8 | **Run and verify frontend tests** | Agent runs `npm test` and fixes any remaining test failures | No | All vitest suites pass |
| 0.9 | **Clean up frontend root junk files** | Agent deletes 25+ dead files: build-err*.txt, lint*.txt, proxy*.js, out*.txt, dep.txt, etc. | No | Frontend root is clean |
| 0.10 | **Verify route-by-route build integrity** | Agent runs `npm run build` and checks all 34 routes compile | No | `npm run build` succeeds with 0 errors |

**Phase 0 Exit Criteria:** Backend `pytest` collects + frontend `npm run build` + `npm test` all pass.

---

## Phase 1: Canonical Documentation Reset

> **Goal:** Docs match codebase reality. No more Vite references, port 5173, Spring Boot gateway claims.

### Agent 2 — Documentation (Agent 1 continues backend hardening in parallel)

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 1.1 | **Rewrite root README.md** | Agent replaces stale content: correct ports (3000 not 5173), Next.js not Vite, NEXT_PUBLIC_*not VITE_*, Python 3.12, correct local setup instructions | No | README matches actual codebase |
| 1.2 | **Rewrite backend/README.md** | Same — correct Python version, correct env vars, correct API base URL, correct run commands | No | Backend README matches reality |
| 1.3 | **Update docs/PRD.md** | Merge Codex findings (34 routes, not 25; stale plan drift) into PRD. Add Codex's "feature-rich but operationally unstable" verdict | No | PRD reflects current state |
| 1.4 | **Update docs/Features.md** | Add Codex findings: items that plans mark TODO but are already done (TipTap on /edit, ThemeToggle unified, Groq fallback, template whitelist complete) | No | Features list is accurate |
| 1.5 | **Update docs/TechStack.md** | Add Python 3.12 pin info, add `@testing-library/dom` to test stack, mention 34 routes | No | TechStack is up to date |
| 1.6 | **Update docs/API.md** | Cross-check against Codex's evidence matrix — add all v1 endpoints with runtime evidence status | No | API docs are truthful |
| 1.7 | **Update docs/Architecture.md** | Remove Spring Boot gateway reference (Codex: "Obsolete / incorrect requirement"). Mark FastAPI-only as current arch | No | Architecture doc is honest |
| 1.8 | **Update docs/Security.md** | Add Codex's finding that security is "better scaffolded than plans claim" but needs live validation | No | Security doc reflects both strengths and gaps |
| 1.9 | **Update docs/Deployment.md** | Add GROBID $0 solution, Render 512MB constraint, 3-tier PDF fallback strategy, correct env var names | No | Deployment guide won't mislead |
| 1.10 | **Update docs/UIUX.md** | Add Codex findings: violet accent drift in live preview, inconsistent icon systems, need for design system guide | No | UIUX doc covers Codex issues |
| 1.11 | **Update docs/comprehensive_audit.md** | Merge Codex-specific findings: Python 3.11.9 issue, pytest import collision details, @testing-library/dom, 34 routes, stale Vite refs, updated ratings (QA: 3/10, DevEx: 4/10, Docs: 3/10) | No | Audit is fully merged |
| 1.12 | **Create docs/Testing.md** (NEW — from Codex) | Document test strategy: unit/integration/llm/service profiles, current blockers, how to run each level | No | New file exists |
| 1.13 | **Create docs/Risk_Register.md** (NEW — from Codex) | Combine Codex's 15 risk items with Antigravity's risk map | No | New file exists |
| 1.14 | **Create docs/Roadmap.md** (NEW — from Codex) | Phase 0-5 roadmap with exit criteria from Codex + my suggestions | No | New file exists |
| 1.15 | **Mark stale docs as deprecated** | Add deprecation notices to: docs/generate_docs.py output, any Vite-era files | No | Stale docs won't mislead |

**Phase 1 Exit Criteria:** All docs match codebase. New contributor can bootstrap without being misled.

---

## Phase 2: Contract & Smoke Validation

> **Goal:** Prove one happy path per product mode.

### Agent 1 — Backend Smoke Tests

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 2.1 | **Add API contract smoke: GET /api/v1/templates** | Write test that verifies 17 templates returned with correct schema | No | Test passes |
| 2.2 | **Add API contract smoke: POST /api/v1/documents/upload** | Write test with fixture file (mock ClamAV) | No | Test passes |
| 2.3 | **Add API contract smoke: GET /api/v1/health** | Verify health endpoint returns correct structure | No | Test passes |
| 2.4 | **Add API contract smoke: generator session CRUD** | Write test for create/get/update session | No | Test passes |
| 2.5 | **Add preview endpoint smoke** | Write test for `/api/v1/preview/live` (HTTP path, not WS) | No | Test passes |
| 2.6 | **Add deprecation header test** | Verify legacy routes return `Deprecation` header | No | Test passes |
| 2.7 | **Add signed download test** | Write test with mock Supabase storage | No | Test passes |

### Agent 2 — Frontend Smoke Tests

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 2.8 | **Fix E2E test stubs** | Review top 20 E2E test files, fill in real assertions for critical paths | No | At least 20 E2E tests have real assertions |
| 2.9 | **Add Playwright smoke: /edit page** | Verify TipTap editor loads, accepts text | No | Test passes |
| 2.10 | **Add Playwright smoke: /results page** | Verify quality score panel renders | No | Test passes |
| 2.11 | **Add Playwright smoke: /live page** | Verify split editor renders | No | Test passes |
| 2.12 | **Add Playwright smoke: /agent page** | Verify agent chat pane renders | No | Test passes |

**Phase 2 Exit Criteria:** Every major mode has at least one trusted happy-path smoke test.

---

## Phase 3: Critical Gap Fixes

> **Goal:** Fix the most impactful code stubs and contract drift.

### Agent 1 — Backend Gaps

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 3.1 | **Expand RBAC middleware** (708B → real) | Implement role checking: admin, pro, free. Add decorator `@require_role("admin")` | No | RBAC works for protected endpoints |
| 3.2 | **Expand audit_log_service.py** (1.1KB → real) | Log all write operations with user, action, resource, IP, timestamp | No | Write ops produce audit log entries |
| 3.3 | **Implement latex_exporter.py** (743B → real) | Add Pandoc subprocess call for DOCX → LaTeX conversion | ️ **YES — Agent asks user:** "Do you want LaTeX export supported now, or should we hide it? If supported, do you have Pandoc installed?" | LaTeX export works OR is hidden from UI |
| 3.4 | **Add GROBID $0 fallback** | Set `GROBID_ENABLED` config, ensure Docling fallback works in orchestrator.py, add `pymupdf` to requirements.txt | No | PDF parsing works without GROBID Docker |
| 3.5 | **Create deploy-staging.yml** | Write GitHub Actions workflow for Render staging deployment | ️ **YES — Agent asks user:** "What's your Render staging service name and deploy hook URL?" | Staging deploy workflow exists |
| 3.6 | **Fix environment config** | Add `GROBID_ENABLED`, `USE_DOCLING_FALLBACK`, `PYMUPDF_FALLBACK` to `.env.example` | No | .env.example is complete |

### Agent 2 — Frontend Gaps

| # | Task | What Agent Does | User Input Needed? | Exit Criteria |
| --- | ------ | ----------------- | ------------------- | --------------- |
| 3.7 | **Implement api.synthesis.js** (36B → real) | Wire up synthesis API service: createSession, getSession, getEvents (SSE) | No | Synthesis UI connects to backend |
| 3.8 | **Fix globals.css bloat** | Replace 6337-line compiled Tailwind with only custom CSS. Let Tailwind JIT generate utilities. | No | globals.css is under 200 lines |
| 3.9 | **Unify template source** | Source template list from backend API, not hardcoded array in frontend live preview | No | Template list is single source of truth |
| 3.10 | **Consolidate component directories** | Move unique files from `frontend/components/` into `frontend/src/components/`, remove duplicate dir | No | Single component directory |
| 3.11 | **Freeze TEX support contract** | ️ **Agent asks user:** "Do you want TEX download visible now? It's partially implemented. We can either: (a) fully support it with tests, or (b) hide it until ready." | **YES** | TEX is either supported+tested or hidden |
| 3.12 | **Add semantic color tokens** | Add success/warning/error/info/secondary colors to tailwind.config.js | No | Design system has semantic tokens |

**Phase 3 Exit Criteria:** All critical stubs are expanded. Contract drift is resolved.

---

## Phase 4: Service-Backed Validation

> **Goal:** Validate code against real services.

| # | Task | Agent | User Input Needed? | Exit Criteria |
| --- | ------ | ------- | ------------------- | --------------- |
| 4.1 | **Test with local Redis** | Agent 1 | ️ **YES — Agent asks user:** "Can you start Redis locally? `docker run -d -p 6379:6379 redis:7-alpine`" | Preview cache + rate limiting work |
| 4.2 | **Test with Supabase** | Agent 1 | ️ **YES — Agent asks user:** "Are your Supabase credentials in .env? Can you confirm the project is accessible?" | Auth + DB operations work |
| 4.3 | **Test Stripe sandbox** | Agent 1 | ️ **YES — Agent asks user:** "Do you have Stripe test keys? Install Stripe CLI: `stripe listen --forward-to localhost:8000/api/v1/billing/webhook`" | Webhook handling works |
| 4.4 | **Test Docling fallback** | Agent 1 | No | PDF parsing works with Docling when GROBID is off |
| 4.5 | **Test full formatter flow** | Agent 2 | ️ **YES — Agent asks user:** "Please start both backend and frontend locally. Then upload a sample DOCX file and select IEEE template." | Upload → process → results → download works |
| 4.6 | **Test full agent flow** | Agent 2 | ️ **YES — Agent asks user:** "Go to /agent page, type: 'Write a short paper about machine learning'. Does the outline appear?" | Prompt → outline → approve → write flow works |

**Phase 4 Exit Criteria:** Core service-backed flows are proven.

---

## Phase 5: Launch Readiness

> **Goal:** Deployable, supportable product.

| # | Task | Agent | User Input Needed? | Exit Criteria |
| --- | ------ | ------- | ------------------- | --------------- |
| 5.1 | **Lock deployment topology** | Both | ️ **YES — Agent asks user:** "Confirm: Vercel (frontend), Render (backend), Supabase (auth/DB), Upstash (Redis). Correct?" | Deployment architecture documented |
| 5.2 | **Set up Vercel deployment** | Agent 2 | ️ **YES — Agent asks user:** "Please connect your GitHub repo to Vercel and share the project URL" | Frontend deploys to Vercel |
| 5.3 | **Set up Render deployment** | Agent 1 | ️ **YES — Agent asks user:** "Please create a Render web service and share the deploy hook URL" | Backend deploys to Render |
| 5.4 | **Configure production env vars** | Both | ️ **YES — Agent asks user:** "Set these env vars in Render: GROBID_ENABLED=false, FORCE_HTTPS=true, etc." | All env vars configured |
| 5.5 | **Run production smoke test** | Both | ️ **YES — Agent asks user:** "Visit the deployed URL and test: upload a document, check formatting" | Production works |

---

## 📋 My Additional Suggestions (Not in any audit)

| # | Suggestion | Why | Priority |
| --- | ----------- | ----- | ---------- |
| S1 | **Add OpenAPI schema auto-generation** | FastAPI generates it, just expose at `/docs` | HIGH — free, instant |
| S3 | **Add health check to deploy-production.yml** | Currently deploys without verifying the app starts | MEDIUM |
| S4 | **Add Zod/Yup schema validation on frontend** | Backend validates, frontend doesn't — inconsistent | MEDIUM |
| S5 | **Add `pre-commit` hooks** | Ruff + ESLint on commit = fewer CI failures | MEDIUM |
| S6 | **Create a `.env.template` generator script** | User always forgets env vars | LOW |
| S7 | **Add WebSocket reconnect with exponential backoff** | Live preview will drop connections in production | HIGH |
| S8 | **Add keyboard shortcuts** | Ctrl+Enter submit, Ctrl+S save — power user productivity | LOW |

---

## Verification Plan

### Automated Tests (Exact Commands)

| Test | Command | Expected |
| ------ | --------- | ---------- |
| Backend Python version | `python --version` in backend venv | `Python 3.12.x` |
| Backend test collection | `python -m pytest --collect-only -q` in `backend/` | No errors, test items listed |
| Backend unit tests | `python -m pytest tests -m "not integration and not llm" -x -q --tb=short` in `backend/` | All passed |
| Frontend build | `npm run build` in `frontend/` | Exit code 0 |
| Frontend unit tests | `npm test` in `frontend/` | All suites pass |
| Frontend lint | `npm run lint` in `frontend/` | No errors |

### Browser Tests (Playwright)

```bash
# Run after both backend and frontend are running
cd frontend
npx playwright test tests/e2e/upload.spec.js --headed
npx playwright test tests/e2e/results.spec.js --headed
npx playwright test tests/e2e/agent.spec.js --headed
```

### Manual Verification (User Does These)

1. **Upload flow:** Go to `/upload` → upload a DOCX → select IEEE → wait for processing → check results → download
2. **Live preview:** Go to `/formatter/live` → type in editor → verify preview updates in right pane
3. **Agent flow:** Go to `/agent` → describe a paper → verify outline → approve → watch sections generate
4. **Dark mode:** Toggle theme → verify all pages look correct in both modes
5. **Guest access:** Open incognito → try uploading without login → verify 5/day limit works

---

## Summary: What Each Agent Owns

### Agent 1 (Backend/Infrastructure)

- Python 3.12 env rebuild
- pytest import collision fix
- Backend test harness
- API contract smoke tests
- RBAC, audit logging, latex export expansion
- GROBID fallback
- deploy-staging.yml
- Service-backed validation (Redis, Supabase, Stripe)

### Agent 2 (Frontend/Docs)

- generate-tests.js fix
- @testing-library/dom install
- Frontend build + test restoration
- All 15 documentation files (create/update)
- globals.css cleanup
- api.synthesis.js implementation
- Component directory consolidation
- Template source unification
- E2E test stub filling
- Playwright smoke tests

---

*Total: ~60 tasks across 6 phases. Estimated time: 3-5 days with two agents working in parallel.*
*Both agents should start Phase 0 simultaneously — Agent 1 on backend, Agent 2 on frontend.*
