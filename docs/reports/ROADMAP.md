# ScholarForm AI — Development Roadmap

> **Status overview.** For the detailed implementation plan with exit criteria, see [docs/reports/FUTURE_ROADMAP.md](docs/reports/FUTURE_ROADMAP.md).

---

## Current Status (July 2026)

- **Version:** 1.0.0 (released July 21, 2026)
- **Backend coverage:** ~61% (1000+ deep tests)
- **Documentation:** Enterprise-grade, 80+ files, 34 gaps closed
- **CI/CD:** 24 GitHub Actions workflows, SLSA Level 3
- **Integrations:** NVIDIA NIM, Groq, Ollama, Supabase, Stripe, Redis, ChromaDB

---

## Short-Term (3 Months) — H2 2026

### Phase 2: Contract & Smoke Validation
- Implement health, templates, upload E2E contract tests
- WebSocket live preview smoke test
- Agent outline → approve → generate E2E
- Synthesis SSE stream test
- Fill 20 critical-path Playwright test stubs

### Phase 3: Critical Gap Fixes
- `api.synthesis.js` — wire from 36B stub to real API calls
- `latex_exporter.py` — implement Pandoc subprocess (743B → full)
- `rbac.py` — implement role-based access control (708B → full)
- `audit_log_service.py` — log all write operations
- `globals.css` — reduce 117KB compiled bloat
- `deploy-staging.yml` — create staging workflow
- Consolidate duplicate `components/` directories

### Phase 4: Service-Backed Validation
- Redis health check integration test
- Supabase Auth signup → login → JWT E2E
- Stripe webhook signature validation
- Docling PDF fallback with real PDF
- ChromaDB RAG with multi-doc synthesis

---

## Medium-Term (6 Months) — H1 2027

### Phase 5: Launch Readiness
- Lock cloud topology: Vercel + Render + Supabase + Upstash
- Staging environment live with health check
- Grafana dashboard: request rate, error rate, queue depth
- RBAC fully implemented for admin, pro, free, guest roles
- OWASP Top 10 security audit — zero HIGH findings
- P99 upload ACK <400ms on staging

### Feature Enhancements
- LaTeX export via Pandoc
- Citation network graph visualization
- Template marketplace (community-contributed templates)
- Batch processing queue management UI
- Collaborative editing (multi-user on same document)
- API rate limit tier management dashboard

---

## Long-Term (12 Months) — 2027

### Platform Scale
- **v2.0** — Breaking API changes (if needed)
- Horizontal scaling for Celery workers
- Read replica support for Supabase PostgreSQL
- Multi-region deployment
- CDN for file storage delivery

### AI Capabilities
- Custom fine-tuned models for academic formatting
- Real-time collaborative AI editing suggestions
- Automated peer review simulation
- Reference auto-completion from 200M+ papers
- Plagiarism detection integration
- Multi-language manuscript support

### Enterprise
- SSO/SAML authentication
- Audit log export (SOC 2 compliant)
- Custom deployment (VPC, private networking)
- Enterprise SLA with dedicated support
- Usage analytics dashboard for organizations
- Admin console for user/team management

### Community
- Plugin system for custom formaters
- VS Code extension for local formatting
- GitHub Actions integration (CI format check)
- CLI tool for headless processing
- Public API with developer portal
- Open-source contributor program

---

## Success Definition

> A new engineer can clone the repo, run tests, start both servers, and format a document — without asking anyone a question.

---

*Last updated: July 2026*
