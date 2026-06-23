<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Contributing to ScholarForm AI

First off, thanks for taking the time to contribute!

## Code of Conduct

This project and everyone participating in it is governed by the [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Report unacceptable behavior to the maintainers.

## How to Contribute

### Reporting Bugs

1. **Check existing issues** to see if the bug has already been reported.
2. **Open a new issue** with a clear title and description. Include:
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots / logs if applicable
   - Environment details (OS, Python version, Node version)

### Suggesting Features

1. Open a feature request issue with:
   - A clear description of the problem you're solving
   - Proposed solution (optional)
   - Alternatives you've considered

### Documentation Contributions

1. All `.md` files must start with YAML frontmatter (see [Style Guide](docs/.docs-style-guide.md)).
2. Keep `last_updated` current — set to the month of your change.
3. Add `sidebar_position` based on the category ordering scheme.
4. Every new page must be added to `docs/README.md` index.
5. Code examples must be tested — if you add a curl command, verify it works against a running instance.
6. Use Mermaid diagrams for architecture and flow documentation (not ASCII art or screenshots of code).
7. **Broken links cause CI failure** — run the freshness check locally before pushing.
8. See the full [Documentation Style Guide](docs/.docs-style-guide.md) for formatting conventions.

### Developer Certificate of Origin

All contributions must include a `Signed-off-by` trailer in every commit, certifying that you have read and agree to the [Developer Certificate of Origin](DEVELOPER_CERTIFICATE_OF_ORIGIN.md) (DCO). Use `git commit -s` to sign off automatically.

By signing off, you certify that you have the right to submit your contribution under the project's MIT license.

### Requirements for Acceptable Contributions

All contributions MUST meet the following standards:

1. **Coding standards**: Python code must pass `ruff check` with no errors. Frontend code must pass `eslint --max-warnings 0`. Type annotations are required for Python (checked by mypy) and TypeScript (checked by tsc).
2. **Test coverage**: All new functionality MUST include corresponding tests. The project maintains minimum 70% coverage (backend) and full coverage on critical paths (frontend).
3. **No regressions**: All existing tests MUST pass before a PR is accepted.
4. **Conventional commits**: All commit messages MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.
5. **Signed commits**: Every commit MUST be signed off (`git commit -s`) to comply with the DCO.
6. **Documentation**: Public API changes MUST include documentation updates.
7. **Security**: Contributions MUST NOT introduce known vulnerable dependencies, hardcoded secrets, or bypass existing security controls.

### Code Review Standards

All pull requests require code review before merging:

1. **Minimum reviewers**: At least one Core Team member must approve.
2. **Review scope**: Reviewers MUST check for correctness, test coverage, security implications, style conformance, and documentation accuracy.
3. **Review response**: Maintainers should respond to PRs within 48 hours (core business days).
4. **Changes requested**: If changes are requested, the author must address them before the PR can be merged.
5. **Self-review**: Authors should self-review their own code before requesting review.

See [Code Review Standards](docs/CODE_REVIEW_STANDARDS.md) for full details.

### Pull Requests

1. **Fork** the repo and create your branch from `main`.
2. **Use the [pull request template](PULL_REQUEST_TEMPLATE.md)** — fill out the checklist.
3. **Sign off your commits** (`git commit -s`) to comply with the DCO.
4. **Build the project first**: run `BUILDING.md` instructions to verify your environment.
5. **Follow code conventions**:
   - Python: Ruff linting, type annotations via mypy
   - Frontend: ESLint with `--max-warnings 0`
6. **Write tests** — we maintain 70%+ coverage. Run:
   ```bash
   cd backend
   pytest tests -m "not integration and not llm" -x -q --cov=app
   ```
7. **Lint your code**:
   ```bash
   cd backend && ruff check app --config ruff.toml
   cd frontend && npm run lint
   ```
8. **Commit using conventional commits**:
   - `feat:` new feature
   - `fix:` bug fix
   - `refactor:` code change without feature/fix
   - `docs:` documentation
   - `test:` adding tests
   - `ci:` CI/CD changes
9. **Open a PR** against `main`. Reference any related issues.

### Code of Conduct Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at conduct@scholarform.com. All complaints will be reviewed and investigated.

## Development Setup

See the [README](README.md#quick-setup) for full setup instructions.

### Quick Start

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## Project Structure

```
backend/
  app/                    # FastAPI application
    routers/              # API routes (34 endpoints)
    services/             # Business logic (25 services)
    pipeline/             # Document processing pipeline
    tasks/                # Celery background tasks
  tests/                  # Pytest test suite
  db/                     # Database migrations & semantic store

frontend/
  src/app/                # Next.js 16 App Router pages
  src/components/         # React components
  src/context/            # React context providers
  e2e/                    # Playwright E2E tests
```

## Questions?

Open a discussion or reach out to the maintainers.
