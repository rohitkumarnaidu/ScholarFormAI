# Project: ScholarFormAI Documentation Upgrade Mission

## Architecture Overview
ScholarFormAI (AMF - Automated Docx Formatter) consists of:
- Backend: FastAPI (`backend/app/main.py`), 16 API routers in `backend/app/routers/v1/`, 48 services in `backend/app/services/`, Pydantic v2 schemas (`api_envelope`), SQLAlchemy ORM models (Supabase PostgreSQL).
- Frontend: Next.js 16 App Router in `frontend/app/`, UI components in `frontend/src/`.
- CLI: Python Click CLI in `cli/amf/`.
- SDK: Synchronous (`AMFClient`) and Asynchronous (`AsyncAMFClient`) Python SDK clients in `sdk/amf_sdk/`.
- Documentation site: Docusaurus framework in `docs/`.

## Enterprise Documentation Standards
- **Mermaid Diagrams**: Every major architectural & reference document MUST contain valid, visually rich Mermaid diagrams (flowcharts, sequence diagrams, ERDs, class diagrams).
- **No Text Collisions**: Node labels must cleanly escape special characters (`|`, `"`, `<br/>`).
- **No Duplicate Files**: Obsolete files like `DATABASE.md` are replaced cleanly by `DATABASE_SCHEMA.md` without leftover duplicates or stale contradictions.
- **Syntactic Integrity**: All code fences properly closed (` ```mermaid `, ` ```bash `, ` ```python `, ` ```json `).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Comprehensive Audit & Gap Analysis | Inventory 70 root docs, backend code, CLI/SDK, frontend, Docusaurus | none | DONE |
| 2 | Base Repository & Standard Docs | README.md, AGENTS.md, CHANGELOG.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md | M1 | DONE |
| 3 | System Architecture & Database Docs | ARCHITECTURE.md, SYSTEM_DESIGN.md, DATABASE_SCHEMA.md, PIPELINE.md | M1 | DONE |
| 4 | API, CLI & SDK Reference Docs | API_REFERENCE.md, CLI_REFERENCE.md, SDK_GUIDE.md, CONFIGURATION.md, TESTING.md, ERROR_CODES.md | M1 | DONE |
| 5 | Docusaurus Site & Doc Sync | Sync docs/docs/ tree with root references; create missing reference/guide pages | M2, M3, M4 | DONE |
| 6 | E2E Verification & Forensic Audit | Verify markdown lint, Mermaid diagram syntax, code block fencing, audit gate | M5 | DONE |

## Code & File Layout
- `.agents/orchestrator/`: Orchestrator state and handoff metadata
- `.agents/teamwork_preview_explorer_m1_1/`: Explorer 1 metadata & audit handoff
- `.agents/teamwork_preview_explorer_m1_2/`: Explorer 2 metadata & audit handoff
- `.agents/teamwork_preview_explorer_m1_3/`: Explorer 3 metadata & audit handoff
- `.agents/teamwork_preview_worker_m2/`: Worker M2 metadata & handoff
- `.agents/teamwork_preview_worker_m3/`: Worker M3 metadata & handoff
- `.agents/teamwork_preview_worker_m4/`: Worker M4 metadata & handoff
- `.agents/teamwork_preview_worker_m5/`: Worker M5 metadata & handoff
- `.agents/teamwork_preview_reviewer_1/`: Reviewer 1 metadata & review verdict
- `.agents/teamwork_preview_reviewer_2/`: Reviewer 2 metadata & review verdict
- `.agents/teamwork_preview_challenger_1/`: Challenger metadata & empirical audit
- `.agents/teamwork_preview_auditor/`: Forensic Auditor metadata & CLEAN verdict
