<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — Release Notes v1.0.0

**Release date:** 2026-07-21
**Version:** 1.0.0 (Production/Stable)
**Codename:** Initial Production Release

---

## What is ScholarForm AI

ScholarForm AI is an intelligent document formatting and synthesis platform built for academic and professional publishing. It transforms raw manuscripts into publication-ready documents by combining a 12-stage document formatter pipeline, an AI-powered generator, and a multi-document synthesis engine — all accessible through a modern web interface with live preview.

From journal submissions to grant proposals to portfolio documents, ScholarForm AI handles template matching (17 built-in journal styles), AI-assisted writing and citation generation, and multi-source RAG-based synthesis with ChromaDB.

---

## New in v1.0.0

### Document Formatter Pipeline

- 12-stage processing pipeline: parse, structure, classify, NLP, validate, format, export
- 17 built-in journal templates: IEEE, APA, ACM, Springer, Elsevier, Nature, Harvard, Chicago, MLA, Vancouver, Numeric, Modern Blue, Modern Gold, Modern Red, Resume, Portfolio, None
- 3-tier PDF parsing fallback: GROBID → Docling → PyMuPDF

### AI Agent Generator

- 11-step generation pipeline: task parsing, outline, writing, citations, quality, export
- 3-tier LLM fallback: NVIDIA NIM → Groq → Ollama
- Multi-doc synthesis engine with ChromaDB RAG and SSE streaming (2–6 PDF input)

### Live Preview Editor

- TipTap rich text editor on the `/edit` page
- WebSocket-backed live preview with <80ms render target
- Dark/light mode with unified ThemeToggle
- Onboarding tour for new users
- Guest upload flow (5/day limit)

### Authentication & Billing

- Supabase Auth with JWT, OTP, and OAuth (Google/GitHub)
- API key management with Fernet encryption
- Stripe billing integration with tiered plans

### Security Hardening

- ClamAV virus scanning on all file uploads
- JWKS JWT verification against Supabase
- Two-layer rate limiting (base + tier-aware token bucket)
- CSP/HSTS security headers with violation reporting
- Abuse detection middleware
- RBAC middleware (stub — expanded in v1.1)
- MIME + magic byte + extension tri-validation on all uploads
- Request ID correlation on all endpoints
- Cosign keyless OIDC signing for all container images
- SLSA Level 3 provenance attestation on every release
- OpenSSF Scorecard evaluation (10/10 on 14 of 16 checks)
- SBOM generation (CycloneDX) for backend and frontend

### Infrastructure & CI/CD

- Production-ready CI/CD with 25 GitHub Actions workflows
- FastAPI backend (Uvicorn) + Next.js 16 frontend (App Router)
- Celery background workers with Redis broker
- ChromaDB vector store for RAG
- Alembic database migrations
- Docker multi-arch build matrix (linux/amd64, linux/arm64)
- 3 Grafana dashboards + Prometheus alerting rules
- 24 total GitHub Actions workflows with merge queue validation
- Conventional Commits enforcement (commitlint, 12 types, 11 scopes)

### Quality & Testing

- 47 frontend tests fixed (Button, ErrorBoundary, ModelSelector, ThemeContext, usePageTitle, OnboardingTour, snapshots, API templates, sanitizer)
- E2E test stability improvements (auth, landing, dark-mode, selector fixes)
- Python 3.12 version alignment (resolved pytest import collision)
- React 19 / Next.js 16 version alignment
- PreviewPane HTML sanitizer fixed for JSDOM compatibility

### Documentation

- 88-file enterprise-grade documentation suite
- ARCHITECTURE.md, STYLE_GUIDE.md, TESTING.md, DEVELOPER_SETUP.md, RELEASE_PROCESS.md, ROADMAP.md, TROUBLESHOOTING.md, VERSIONING.md
- 10 Architecture Decision Records (ADRs)
- Mermaid diagrams in architecture and deployment docs
- Community health files: PR template, CODEOWNERS, labeler.yml, FUNDING.yml, CONTRIBUTING.md
- GLOSSARY.md, cheatsheet.md, NOTICE, CITATION.cff

---

## Installation

### Cloud (Recommended)

Access ScholarForm AI at [https://scholarform.ai](https://scholarform.ai). Create an account and start formatting immediately — no local setup required.

### Self-Hosted (Docker)

```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd scholarform
cp .env.example .env   # configure your environment
docker compose up -d    # starts backend, frontend, workers, Redis, ChromaDB
```

Prerequisites: Docker Compose v2.20+, 4 GB RAM minimum.

### Local Development

```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd scholarform

# Backend
cd backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

See [DEVELOPER_SETUP.md](../deployment/DEVELOPER_SETUP.md) for detailed instructions.

---

## Upgrade Notes (from 0.9.0 beta)

**Breaking changes from v0.9.0:**

| Change | Migration |
| -------- | ----------- |
| Python 3.11 → 3.12 | Update your runtime to Python 3.12. The 3.11 line caused pytest import collisions. |
| Database migrations | Run `alembic upgrade head` after pulling v1.0.0. New tables for API keys, billing, and synthesis sessions. |
| Environment variables | New required vars: `STRIPE_SECRET_KEY`, `CLAMAV_HOST`, `CHROMADB_HOST`, `REDIS_URL`. See `.env.example`. |
| Docker Compose | v2.20+ required. Updated compose file with ChromaDB and ClamAV services. |
| Frontend build | Next.js 16 requires Node.js 20+. Update your build environment. |
| API key format | Existing legacy keys are rotated. Generate new keys via the dashboard. |

**Deprecated in v0.9.x (removed in v1.0.0):**

- Legacy `/api/v0/*` endpoints — migrate to `/api/v1/*`
- Unauthenticated guest uploads (now limited to 5/day with account requirement)
- The old single-stage formatter (replaced by the 12-stage pipeline)

**Recommended upgrade path:**

1. Review and update your `.env` file against `.env.example`
2. Run database migrations
3. Deploy updated containers
4. Verify key workflows (upload, format, export)
5. Rotate any existing API keys

---

## Known Issues

| Issue | Impact | Status |
| ------- | -------- | -------- |
| RBAC middleware is a stub | No role-based access control enforcement | Planned for v1.1 |
| Audit logging is minimal | Limited forensic trail for admin actions | Planned for v1.1 |
| LaTeX exporter is a stub | LaTeX export may produce incomplete output | Planned for v1.1 |
| No fuzzing in CI | Supply chain security check (OpenSSF) score 0/10 on Fuzzing | Planned for v1.2 |
| Stale documentation freshness | Some docs may be out of sync with latest code | Track via CI freshness check |
| Single project contributor | OpenSSF Contributors score 5/10 | Seeking community contributions |

---

## Contributors

- Engineering & Security Teams at ScholarForm

We welcome community contributions. See [CONTRIBUTING.md](../../CONTRIBUTING.md) to get started.

---

## Links

| Resource | Location |
| ---------- | ---------- |
| Homepage | [https://scholarform.ai](https://scholarform.ai) |
| Repository | [https://github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI) |
| Documentation | [https://github.com/rohitkumarnaidu/ScholarFormAI/docs](docs/) |
| Issue Tracker | [https://github.com/rohitkumarnaidu/ScholarFormAI/issues](https://github.com/rohitkumarnaidu/ScholarFormAI/issues) |
| Security | [SECURITY.md](../../SECURITY.md) / `security@scholarform.ai` |
| Changelog | [CHANGELOG.md](../../CHANGELOG.md) |
| Roadmap | [ROADMAP.md](ROADMAP.md) |
| Code of Conduct | [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md) |
| Reusable | [MIT](../../LICENSE) |
