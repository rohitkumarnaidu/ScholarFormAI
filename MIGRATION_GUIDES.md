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
