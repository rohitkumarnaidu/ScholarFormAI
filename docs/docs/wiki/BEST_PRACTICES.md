<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---
title: ScholarForm AI — Development Best Practices
description: Code style, testing, git workflow, PR review, and security best practices for contributors
sidebar_position: 3
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# Development Best Practices

> **See also:** [Coding Standards](../CODING_STANDARDS.md), [Code Review Standards](../CODE_REVIEW_STANDARDS.md), [Testing Strategy](../Testing.md), [Security](../Security.md)

---

## Code Style Guide

### Python (Backend)

- **Formatter & Linter:** [ruff](https://docs.astral.sh/ruff/) — configured in `backend/pyproject.toml`
- **Type Hints:** Required for all function signatures (PEP 484)
- **Imports:** Group as standard library, third-party, local; use absolute imports
- **Docstrings:** Google-style docstrings for public modules, classes, and functions
- **Max Line Length:** 100 characters (enforced by ruff)
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants

Run linting before committing:

```bash
cd backend
ruff check app
ruff format --check app
```

### TypeScript / JavaScript (Frontend)

- **Formatter:** Prettier with project config — `npm run format`
- **Linter:** ESLint with Next.js config — `npm run lint`
- **TypeScript:** Strict mode enabled; avoid `any` unless absolutely necessary
- **Naming:** `camelCase` for functions/variables, `PascalCase` for components/types
- **File Structure:** One component per file; colocate tests as `*.test.tsx`

Run linting before committing:

```bash
cd frontend
npm run lint
npm run typecheck
```

### General

- No commented-out code — delete it
- No `print()` / `console.log()` in committed code — use the logging framework
- Keep functions small and single-purpose; extract helpers where appropriate
- Follow existing patterns in the codebase — consistency over preference

---

## Testing Best Practices

### Coverage Targets

| Tier | Target | Current |
|------|--------|---------|
| Backend critical paths | 90%+ | ~21% (in progress) |
| Backend overall | 70%+ | ~21% |
| Frontend components | 70%+ | Being established |
| E2E critical flows | 100% coverage | Being established |

### What to Test

- **Formatting pipeline:** Each stage in the 12-stage pipeline must have unit tests
- **AI agent pipeline:** Each of the 11 steps must have integration tests
- **API endpoints:** Every router must have at least a 200-response test
- **Edge cases:** Empty documents, malformed files, concurrent requests
- **Security:** Auth bypass attempts, XSS payloads, rate limit enforcement

### Running Tests

```bash
# Backend
cd backend
pytest                                           # All tests
pytest -m unit                                   # Unit tests only
pytest -m integration                            # Integration tests only
pytest tests/pipeline/ --cov=app/pipeline        # Pipeline coverage

# Frontend
cd frontend
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright E2E tests
```

See [Testing Strategy](../Testing.md) and [Testing Architecture](../TESTING_ARCHITECTURE.md) for the complete testing framework.

---

## Git Workflow

### Branching Model

```
main          ─── Production-ready code
  └── develop ─── Integration branch
       ├── feat/xxx     ─── Feature branches
       ├── fix/xxx      ─── Bug fix branches
       ├── chore/xxx    ─── Maintenance tasks
       └── docs/xxx     ─── Documentation changes
```

### Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add IEEE template support
fix: resolve table overflow in PDF rendering
docs: update API reference for v2 endpoints
chore: bump ruff to 0.9.0
test: add pipeline stage 7 integration tests
```

All commits must be **signed** (GPG or SSH). See [Branch Protection](../runbooks/branch-protection.md).

### Commit Checklist

- [ ] Run linter — no new warnings
- [ ] Run full test suite — all passing
- [ ] Sign the commit
- [ ] Write a meaningful commit message (Conventional Commits format)
- [ ] Keep commits focused on a single change

---

## PR Review Guidelines

### For Authors

- Keep PRs small (under 400 lines preferred, under 1000 lines max)
- Write a clear description: what, why, and how to test
- Link related issues and ADRs
- Request specific reviewers from the [MAINTAINERS.md](../../MAINTAINERS.md)

### For Reviewers

- Review within 1 business day (see [SLO Definitions](../SLO_DEFINITIONS.md))
- Check for:
  - Correctness — does the code do what it claims?
  - Security — no introduced vulnerabilities
  - Performance — no obvious N+1 queries or O(n^2) patterns
  - Test coverage — new code should have tests
  - Style — matches project coding standards
- Be constructive and specific in feedback
- Approve only when all concerns are addressed

See [Code Review Standards](../CODE_REVIEW_STANDARDS.md) for the full review checklist.

### PR Merge Requirements

- ✅ At least one approving review from a maintainer
- ✅ All CI checks passing (lint, test, build, security scan)
- ✅ No merge conflicts with `main`
- ✅ Branch is up to date with `main`

---

## Security Best Practices

### Code Security

- Never commit secrets, API keys, or tokens — use `.env` files and GitHub Secrets
- Validate all user input — especially file uploads (check MIME type, size, content)
- Use parameterized queries for all database operations
- Apply rate limiting to all public endpoints
- Sanitize HTML output to prevent XSS
- Use Supabase RLS policies for data access control

### Supply Chain Security

- Run `npm audit` and `pip-audit` regularly
- Keep dependencies updated via Renovate bot
- Review SBOM in `sbom/` before each release
- Verify SLSA provenance for container images

### Operational Security

- Rotate secrets on a 90-day cadence (see [Secret Rotation](../SECRET_ROTATION.md))
- Enable MFA on all production accounts
- Monitor failed authentication attempts
- Follow the [Security Checklist](../SECURITY_CHECKLIST.md) before each deployment

Refer to [Security Architecture](../SECURITY_ARCHITECTURE.md) for the full threat model and [Security Review](../SECURITY_REVIEW.md) for audit findings.

---

## Documentation Standards

- All `.md` files must include SPDX header and YAML frontmatter
- Frontmatter requires: `title`, `description`, `sidebar_position`, `status`, `owner`, `review_cadence`, `last_updated`
- Use relative links to reference other docs (e.g., `../Security.md`)
- Keep documentation up to date with code changes — update docs in the same PR
- See [Docs Style Guide](../.docs-style-guide.md) for formatting rules

---

## Performance Guidelines

- Avoid blocking the event loop in Python (use async/await)
- Use Celery for long-running tasks (document formatting, AI generation)
- Cache expensive operations (template parsing, LLM responses)
- Optimize database queries — add indexes for frequent query patterns
- Profile before optimizing; use the metrics in [Monitoring & Observability](../MONITORING_OBSERVABILITY.md)
