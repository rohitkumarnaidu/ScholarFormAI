# ScholarForm AI — Code Style Guide

> **Quick reference.** For the full standard (841 lines), see [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md). For docs style, see [docs/.docs-style-guide.md](docs/.docs-style-guide.md).

---

## Python (Backend)

### Runtime

- Python **3.12.x only** (3.11 causes pytest import collisions)
- All `.py` files start with `from __future__ import annotations`
- License header: `# SPDX-License-Identifier: MIT` + `# Copyright (c) 2026 ScholarForm AI`

### Formatting & Linting

- **Formatter:** `ruff format` (line length: 120)
- **Linter:** `ruff check` (configured in `backend/ruff.toml`)
- **Types:** `mypy --strict` (configured in `backend/mypy.ini`)
- Run: `cd backend && ruff check app && mypy app`

### Naming

| Element | Convention | Example |
| --------- | ----------- | --------- |
| Modules | `snake_case` | `document_service.py` |
| Classes | `PascalCase` | `DocumentFormatter` |
| Functions | `snake_case` | `format_document()` |
| Variables | `snake_case` | `job_id` |
| Constants | `UPPER_SNAKE` | `MAX_FILE_SIZE` |
| Private | `_prefix` | `_validate_schema()` |

### Imports (sorted by `ruff`)

1. `from __future__ import annotations`
2. Standard library (`os`, `json`)
3. Third-party (`fastapi`, `sqlalchemy`)
4. First-party (`app.models`, `app.services`)
5. Relative (avoid — use absolute)

### Type Annotations

- Required on all function signatures (enforced by `mypy`)
- Use `|` for unions: `str | None` (PEP 604)
- Use `Self` return type for class methods
- `cast()` and `# type: ignore[arg-type]` with justification comments

### Error Handling

- Use custom exceptions in `app/utils/exceptions.py`
- Always use `detail=` in HTTPException
- Log before raising with correlation ID

---

## TypeScript / JavaScript (Frontend)

### Runtime

- Node.js 20+ (LTS)
- TypeScript with `strict: true`
- ES2022 target, ES modules

### Formatting & Linting

- **Linter:** ESLint (`--max-warnings 0`)
- **Config:** `frontend/.eslintrc.json`
- Run: `cd frontend && npm run lint`
- TypeScript: `npx tsc --noEmit`

### Naming

| Element | Convention | Example |
| --------- | ----------- | --------- |
| Components | `PascalCase` | `DocumentUploader.tsx` |
| Hooks | `camelCase`, `use` prefix | `useLivePreviewSocket` |
| Functions | `camelCase` | `formatDocument()` |
| Types/Interfaces | `PascalCase` | `UploadResponse` |
| Constants | `UPPER_SNAKE` | `MAX_RETRY_COUNT` |
| Files (components) | `PascalCase` | `Stepper.tsx` |
| Files (utilities) | `camelCase` | `formatDate.ts` |

### React Conventions

- Functional components with hooks (no class components)
- Props interface defined above component
- Server components by default; `'use client'` only when needed
- TanStack Query for server state
- Context providers for global state (auth, theme, toast)

---

## Git & Commits

### Conventional Commits

```
<type>(<scope>): <description>

[optional body]
```

| Type | Usage |
| ------ | ------- |
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change without feature/fix |
| `docs` | Documentation |
| `test` | Adding tests |
| `ci` | CI/CD changes |
| `perf` | Performance |
| `security` | Security fix |

Scopes: `backend`, `frontend`, `docs`, `docker`, `ci-cd`, `auth`, `pipeline`, `api`, `db`, `templates`, `deps`

### Requirements

- **Signed commits**: `git commit -s` (DCO sign-off required)
- **One commit per logical change**
- PRs must pass CI before merge

---

## Documentation Standards

- Every `.md` file must have YAML frontmatter (title, description, sidebar_position, version, status, owner, review_cadence, last_updated)
- Use Mermaid for diagrams (not ASCII art or screenshots)
- Links must be relative, not absolute paths
- Code examples must be tested
- See [docs/.docs-style-guide.md](docs/.docs-style-guide.md) for full details

---

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

1. `ruff check` + `ruff format` — Python
2. `eslint` — JavaScript/TypeScript
3. `detect-secrets` — secret scanning

```bash
pip install pre-commit
pre-commit install
```

---

*Last updated: July 2026*
