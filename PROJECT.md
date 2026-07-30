# Project: ScholarFormAI Enterprise Update Management System

## Architecture Overview
ScholarFormAI Enterprise Update Management System provides a unified, cross-platform update infrastructure covering:
- **Backend API & Service Layer**: `backend/app/services/update_service.py`, `backend/app/routers/v1/updates.py`, database models/migrations for channels, releases, update history, and rollback tracking. Built on Pydantic v2 with standard `api_envelope` responses, GitHub Releases API integration (live + cached fallback), semver parsing/comparison, mandatory & security update flags, and SHA-256 + ED25519/RSA signature verification.
- **Frontend Web UI**: Next.js 16 App Router UI in `frontend/app/` and `frontend/src/components/updates/`:
  - `UpdateBanner.tsx` for global update notifications
  - `DashboardUpdateWidget.tsx` for current status, channel, and direct update triggers
  - `UpdateSettingsPage` (`frontend/app/settings/updates/page.tsx` or similar) for channel selection, schedule configuration, auto-update toggle, update history log, and manual check
  - `DownloadProgressTracker.tsx` for background download & installation tracking
- **CLI & Desktop Integration**:
  - `cli/amf/commands/update.py` enhanced with `check`, `channel`, `download`, `verify`, `install`, `offline`, and `rollback` subcommands with retry/backoff resilience
  - Desktop update integration hook / service bridge for native desktop application auto-updates
- **Comprehensive Documentation**: 5 dedicated architecture & user guides in `docs/`: `UPDATE_ARCHITECTURE.md`, `UPDATE_SCHEMA.md`, `UPDATE_DEVELOPER_GUIDE.md`, `UPDATE_USER_GUIDE.md`, `UPDATE_DEPLOYMENT_GUIDE.md`.
- **Test Suite & CI/CD Verification**: `backend/tests/test_updates.py` testing update channel management, semver logic, signature validation, GitHub fallback, and rollback flows.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Backend Service, Database & API | `update_service.py`, `routers/v1/updates.py`, models, DB migrations, semver, GitHub Releases fallback, cryptographic verification (SHA-256 + ED25519/RSA), Pydantic v2 schemas | none | IN_PROGRESS |
| 2 | Frontend Web UI Components | Update Banner component, Dashboard Widget, Update Settings page, background download & progress tracking UI components | M1 | DONE |
| 3 | CLI & Desktop Update Integration | Enhanced `cli/amf/commands/update.py` (check, channel, verify, retry/resilience download, offline update, rollback), Desktop bridge | M1 | IN_PROGRESS |
| 4 | Technical Guides & Test Suites | 5 Architecture/User guides in `docs/` (`UPDATE_ARCHITECTURE.md`, `UPDATE_SCHEMA.md`, `UPDATE_DEVELOPER_GUIDE.md`, `UPDATE_USER_GUIDE.md`, `UPDATE_DEPLOYMENT_GUIDE.md`), `backend/tests/test_update_service.py` | M1, M2, M3 | IN_PROGRESS |
| 5 | Empirical Challenge, Verification & Forensic Audit | `py_compile` backend validation, `npm run build` frontend validation, Challenger stress testing, Forensic Auditor integrity verification | M1, M2, M3, M4 | PLANNED |

## Code & File Layout
- `backend/app/services/update_service.py`: Core update business logic, GitHub API caching, crypto verification, rollback tracking
- `backend/app/routers/v1/updates.py`: FastAPI endpoints for update checking, listing channels, setting preferences, trigger update, rollback
- `backend/app/schemas/update.py`: Pydantic v2 schemas adhering to `api_envelope`
- `backend/app/models/update.py` / migrations: Supabase/SQLAlchemy update schema models
- `frontend/src/components/updates/`: React components for Banner, Dashboard Widget, Progress Tracker
- `frontend/app/settings/updates/page.tsx`: Next.js 16 Settings page
- `cli/amf/commands/update.py`: Click CLI update commands
- `backend/app/services/desktop_update_bridge.py`: Desktop application IPC / bridge hook
- `docs/UPDATE_ARCHITECTURE.md`, `docs/UPDATE_SCHEMA.md`, `docs/UPDATE_DEVELOPER_GUIDE.md`, `docs/UPDATE_USER_GUIDE.md`, `docs/UPDATE_DEPLOYMENT_GUIDE.md`: Comprehensive guides
- `backend/tests/test_updates.py`: Unit and integration test suite for backend update service
