---
title: Changelog
description: Full release history of ScholarFormAI — Automated Manuscript Formatter
---

# Changelog

All notable changes to **ScholarFormAI — Automated Manuscript Formatter** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] — 2026-06-14

### ✨ Added

- **GitHub Packages** — Multi-arch Docker images (`linux/amd64`, `linux/arm64`) published to `ghcr.io/scholarform` with cosign signing + SBOM attestation
- **GitHub Packages (npm)** — Frontend published as `@scholarform/frontend`
- **GitHub Packages (PyPI)** — Backend published to GitHub Packages PyPI registry
- **Release automation** — Release Drafter auto-generates release notes on tag push
- **Conventional Commits** — Commitlint enforces structured commit messages on every PR
- **OpenSSF Scorecard** — Weekly supply chain security evaluation with badge
- **CodeQL analysis** — Python + JavaScript semantic analysis on every push
- **SLSA Level 3 provenance** — Build integrity attestation on all releases
- **CVE advisory workflow** — Auto-creates GitHub Issues from Dependabot alerts
- **Stale issue management** — Auto-closes stale issues (60d) and PRs (30d)
- **PR labeler** — Auto-labels PRs by changed file paths (14 rules + size detection)
- **Merge queue** — Multi-workflow CI validation before merge

### 🔒 Security

- OpenSSF Scorecard: 10/10 on 14 of 16 checks
- CodeQL analysis on every push with security-and-quality query suite
- Cosign keyless OIDC signing for all container images
- SLSA Level 3 provenance attestation on every release
- Trivy filesystem scan in CI

### 🏗️ Infrastructure

- 11 new GitHub Actions workflows (total: 24)
- Docker multi-arch build matrix with QEMU + Buildx
- GitHub Container Registry (`ghcr.io`) integration

---

## [1.0.0] — 2026-07-21

### ✨ Added

- Enterprise pipeline decomposition: orchestrator phases, repository pattern, shared constants
- Production hardening across security, observability, and reliability (20 issues resolved)
- CI/CD RC blockers resolved: security.yml reference, deploy_id output, docker matrix propagation
- Comprehensive community health files: PR template, CODEOWNERS, labeler.yml, FUNDING.yml
- Documentation suite: ARCHITECTURE.md, STYLE_GUIDE.md, TESTING.md, DEVELOPER_SETUP.md, RELEASE.md, ROADMAP.md, TROUBLESHOOTING.md, VERSIONING.md
- Versioning policy and release process documentation
- Release Candidate Readiness Report

### 🐛 Fixed

- 47 frontend tests fixed (Button, ErrorBoundary, ModelSelector, ThemeContext, usePageTitle, OnboardingTour)
- PreviewPane HTML sanitizer fixed for JSDOM compatibility
- DashboardStats export naming mismatch resolved
- API v1.1 functions properly exported (`generateIdempotencyHash`, `getIdempotencyKey`)
- Email domain unified to `@scholarform.ai` across `SECURITY.md`

### 🔄 Changed

- Backend version: `0.1.0` → `1.0.0` (Production/Stable)
- Frontend version: `0.1.0` → `1.0.0`
- Development status: Alpha → **Production/Stable**

### 🔒 Security

- CI/CD security workflow reference fixed
- Container signing matrix outputs properly propagated
- NOTICE file added for third-party attribution

### 🏗️ Infrastructure

- Production-ready CI/CD with 25 workflows
- 3 Grafana dashboards deployed
- Prometheus alerting rules configured
- Docker multi-arch build matrix (`linux/amd64`, `linux/arm64`)
- Cosign keyless signing + SLSA L3 provenance
- SBOM generation (CycloneDX) for backend and frontend

---

## [1.0.0-rc.1] — 2026-06-13

### ✨ Added

- Document formatter pipeline (12-stage: parse → structure → classify → NLP → validate → format → export)
- 17 built-in journal templates (IEEE, APA, ACM, Springer, Elsevier, Nature, Harvard, Chicago, MLA, Vancouver, and more)
- AI Agent generator (11-step pipeline: task parsing → outline → writing → citations → quality → export)
- Multi-doc synthesis engine (ChromaDB RAG, SSE streaming, 2–6 PDF input)
- Live preview WebSocket editor with <80ms render target
- Supabase Auth (JWT, OTP, OAuth Google/GitHub)
- API key management with Fernet encryption
- Stripe billing integration
- TipTap rich text editor on `/edit` page
- Dark/light mode with unified ThemeToggle
- Onboarding tour for new users
- Guest upload flow (5/day limit)

### 🔒 Security

- ClamAV virus scanning on uploads
- JWKS JWT verification against Supabase
- Two-layer rate limiting (base + tier-aware)
- CSP/HSTS security headers middleware
- MIME + magic byte + extension tri-validation

### 🏗️ Infrastructure

- FastAPI backend with Uvicorn on Render
- Next.js 16 (App Router) frontend on Vercel
- Celery background workers with Redis broker
- ChromaDB vector store for RAG
- 3-tier PDF parsing fallback (GROBID → Docling → PyMuPDF)
- 3-tier LLM fallback (NVIDIA NIM → Groq → Ollama)

---

## [0.9.0] — 2026-03-18

### ✨ Added

- Initial public beta release
- Core formatter pipeline with 8-stage processing
- 15 journal templates
- Basic auth (Supabase JWT)
- SSE progress streaming
- Frontend with 34 App Router routes

### ⚠️ Known Issues

- Python 3.11.9 caused pytest import collision — required 3.12
- 93 E2E test files existed but most were <700B stubs
- RBAC middleware was stub (708B)
- Audit logging was minimal (1.1KB)
