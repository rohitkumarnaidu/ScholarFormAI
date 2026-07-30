<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Changelog

All notable changes to ScholarForm AI are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-07-21

### Added

- Enterprise pipeline decomposition: orchestrator phases, repository pattern, shared constants
- Production hardening across security, observability, and reliability (20 issues resolved)
- CI/CD RC blockers resolved: security.yml reference, deploy_id output, docker matrix propagation
- Comprehensive community health files: PR template, CODEOWNERS, labeler.yml, FUNDING.yml
- Documentation suite: ARCHITECTURE.md, STYLE_GUIDE.md, TESTING.md, DEVELOPER_SETUP.md, RELEASE.md, ROADMAP.md, TROUBLESHOOTING.md, VERSIONING.md
- Versioning policy (VERSIONING.md) and release process (RELEASE_PROCESS.md)
- Browser support configuration (.browserslistrc)
- Release Candidate Readiness Report (RC_READINESS_REPORT.md)

### Fixed

- 47 frontend tests fixed (Button, ErrorBoundary, ModelSelector, ThemeContext, usePageTitle, OnboardingTour, snapshots, API templates, sanitizer)
- 8 remaining frontend test failures resolved (headless, error-states, visual-regression)
- PreviewPane HTML sanitizer fixed for JSDOM compatibility
- DashboardStats export naming mismatch resolved
- API v1.1 functions properly exported (generateIdempotencyHash, getIdempotencyKey)
- Email domain unified to @scholarform.ai across SECURITY.md

### Changed

- Backend version: 0.1.0 → 1.0.0 (Production/Stable status)
- Frontend version: 0.1.0 → 1.0.0
- Development status: Alpha → Production/Stable
- unified version across all components (backend, frontend, CITATION.cff)

### Security

- SECURITY.md email domain unified to @scholarform.ai
- CI/CD security workflow reference fixed
- Container signing matrix outputs properly propagated
- NOTICE file added for third-party attribution

### Infrastructure

- Production-ready CI/CD with 25 workflows
- 3 Grafana dashboards deployed
- Prometheus alerting rules configured
- Docker multi-arch build matrix (linux/amd64, linux/arm64)
- Cosign keyless signing + SLSA L3 provenance
- SBOM generation (CycloneDX) for both backend and frontend

## [1.1.0] — 2026-06-14 (pre-release)

### Added

- **GitHub Packages** — Multi-arch Docker images (linux/amd64, linux/arm64) published to `ghcr.io/scholarform` with cosign signing + SBOM attestation
- **GitHub Packages (npm)** — Frontend published as `@scholarform/frontend` to GitHub Packages npm registry
- **GitHub Packages (PyPI)** — Backend published to GitHub Packages PyPI registry
- **Release automation** — Release Drafter auto-generates release notes; tag push triggers full release with SBOM, checksums, SLSA provenance
- **Conventional Commits** — Commitlint enforces structured commit messages on every PR (12 types, 11 scopes)
- **OpenSSF Scorecard** — Weekly supply chain security evaluation with badge
- **CodeQL analysis** — Python + JavaScript semantic analysis on every push
- **SLSA Level 3 provenance** — Build integrity attestation on all releases
- **CVE advisory workflow** — Auto-creates GitHub Issues from Dependabot alerts + pip/npm audit reports
- **Stale issue management** — Auto-closes stale issues (60d) and PRs (30d) with priority/security exemptions
- **PR labeler** — Auto-labels PRs by changed file paths (14 rules + size detection)
- **Merge queue** — Multi-workflow CI validation before merge
- **Branch protection docs** — `docs/BRANCH_PROTECTION.md` with per-branch rules
- **Enterprise GitHub setup guide** — `docs/ENTERPRISE_GITHUB_SETUP.md` (10 sections, 24 workflows)
- **Dependabot groups** — Grouped patch/minor updates, auto-merge for dev dependencies

### Security

- OpenSSF Scorecard evaluation: 10/10 on 14 of 16 checks
- CodeQL analysis on every push with security-and-quality query suite
- Cosign keyless OIDC signing for all container images
- SLSA Level 3 provenance attestation on every release
- Trivy filesystem scan in CI
- Dependabot grouped updates with auto-merge for patches

### Infrastructure

- 11 new GitHub Actions workflows (total: 24)
- Docker multi-arch build matrix with QEMU + Buildx
- GitHub Container Registry (ghcr.io) integration
- Merge queue validation (backend-ci, frontend-ci, security, commitlint, dependency-review)
- Stale issue/PR lifecycle management
- PR auto-labeling by component (backend, frontend, docs, docker, ci-cd, etc.)
- CVE tracking via auto-generated GitHub Issues

### Documentation

- `docs/ENTERPRISE_GITHUB_SETUP.md` — Complete GitHub configuration guide
- `docs/BRANCH_PROTECTION.md` — Branch protection rules for all branch types
- `commitlint.config.js` — Conventional Commits configuration
- `.github/release-drafter.yml` — Release note category templates
- `.github/labeler.yml` — 14 auto-label rules

### Changed

- `README.md` — 8 new badges: Scorecard, CodeQL, SLSA, ghcr.io, GitHub Release, Conventional Commits, Signed Commits
- `SECURITY.md` — Added CVE process, SLSA Level 3, OpenSSF Scorecard, GitHub Security Features table
- `.github/dependabot.yml` — Added grouped updates, auto-merge groups, chromadb ignore

---

## [1.0.0-rc.1] — 2026-06-13

### Added

- Document formatter pipeline (12-stage: parse, structure, classify, NLP, validate, format, export)
- 17 built-in journal templates (IEEE, APA, ACM, Springer, Elsevier, Nature, Harvard, Chicago, MLA, Vancouver, Numeric, Modern Blue, Modern Gold, Modern Red, None, Resume, Portfolio)
- AI Agent generator (11-step pipeline: task parsing, outline, writing, citations, quality, export)
- Multi-doc synthesis engine (ChromaDB RAG, SSE streaming, 2-6 PDF input)
- Live preview WebSocket editor with <80ms render target
- Supabase Auth (JWT, OTP, OAuth Google/GitHub)
- API key management with Fernet encryption
- Stripe billing integration
- TipTap rich text editor on `/edit` page
- Dark/light mode with unified ThemeToggle
- Onboarding tour for new users
- Guest upload flow (5/day limit)

### Security

- ClamAV virus scanning on uploads
- JWKS JWT verification against Supabase
- Two-layer rate limiting (base + tier-aware)
- CSP/HSTS security headers middleware
- Abuse detection middleware
- RBAC middleware (stub — expanded in v1.1)
- Audit logging (minimal — expanded in v1.1)
- MIME + magic byte + extension tri-validation
- Request ID correlation on all endpoints

### Infrastructure

- FastAPI backend with Uvicorn on Render
- Next.js 16 (App Router) frontend on Vercel
- Celery background workers with Redis broker
- ChromaDB vector store for RAG
- Alembic database migrations
- 3-tier PDF parsing fallback (GROBID → Docling → PyMuPDF)
- 3-tier LLM fallback (NVIDIA NIM → Groq → Ollama)
- CI/CD: ruff, mypy, pytest, ESLint, vitest, Playwright
- Pre-commit hooks (ruff, eslint, detect-secrets)
- Docker Compose for local development

### Documentation

- Enterprise-grade docs overhaul (88 files)
- YAML frontmatter on all documentation
- docs/README.md index portal
- Architecture Decision Records (10 ADRs)
- GLOSSARY.md terminology reference
- cheatsheet.md quick-reference card
- .docs-style-guide.md for contributors
- Mermaid diagrams in architecture and deployment docs
- CI freshness check for documentation staleness
- SECURITY.md vulnerability disclosure policy
- CHANGELOG.md (this file)

### Fixed

- Python 3.12 pin for backend (resolved pytest import collision)
- React 19 / Next.js 16 version alignment
- Vite → Next.js references across all docs
- E2E test stability (auth/landing/dark-mode/selector fixes)
- Empty `docs/security/` directory removed
- Absolute `file:///C:/...` paths replaced with relative
- Dashboard URL placeholders marked as not-yet-deployed
- API.md curl examples added for all endpoints

---

## [0.9.0] — 2026-03-18

### Added

- Initial public beta release
- Core formatter pipeline with 8-stage processing
- 15 journal templates
- Basic auth (Supabase JWT)
- SSE progress streaming
- Frontend with 34 App Router routes

### Known Issues (v0.9)

- Python 3.11.9 caused pytest import collision — required 3.12
- 93 E2E test files existed but most were <700B stubs
- RBAC middleware was 708B stub
- Audit logging was 1.1KB minimal
- LaTeX exporter was 743B stub
- api.synthesis.js was 36B empty stub
- deploy-staging.yml missing
- Grafana dashboards not set up
