<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — Coding Standards

> **Canonical source of truth for all code in the ScholarForm AI monorepo.**
> Every PR must conform to every section below; CI enforces compliance automatically.

---

## Table of Contents

1. [Language Versions & Runtimes](#1-language-versions--runtimes)
2. [Code Style & Formatting](#2-code-style--formatting)
3. [Naming Conventions](#3-naming-conventions)
4. [Import Style](#4-import-style)
5. [Type Hints](#5-type-hints)
6. [Documentation & Licensing](#6-documentation--licensing)
7. [Testing Standards](#7-testing-standards)
8. [Git Conventions](#8-git-conventions)
9. [Pre-commit Hooks](#9-pre-commit-hooks)
10. [Error Handling](#10-error-handling)
11. [Security & Secrets](#11-security--secrets)
12. [File Structure & Encoding](#12-file-structure--encoding)

---

## 1. Language Versions & Runtimes

| Layer       | Runtime          | Version Pin            | Config File(s)                        |
|-------------|------------------|------------------------|---------------------------------------|
| **Backend** | Python           | `>=3.12, <3.13`        | `backend/pyproject.toml`              |
| **Frontend** | Node.js         | `>=20` (LTS)           | `frontend/package.json` (engines)     |
| **Frontend** | TypeScript       | `ES2017` target, `strict: true` | `frontend/tsconfig.json`       |
| **Frontend** | JavaScript       | ES2022 (module)         | `frontend/jsconfig.json`              |
| **Infra**   | Docker           | Alpine-based            | `Dockerfile` (backend), `Dockerfile` (frontend) |

### 1.1 Backend (Python 3.12)

- Python **3.12.x only** (3.11 causes pytest import collisions).
- All `.py` files must start with `from __future__ import annotations` to enable PEP 604 (forward references, lazy evaluation of annotations).
- Virtual environment: `.venv` at `backend/.venv`.

```python
# ✅ Correct file preamble
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import ...
```

### 1.2 Frontend (Next.js 16 + React 19)

- **Framework:** Next.js 16 (App Router), React 19 — NOT Vite.
- Dev server: `next dev --turbopack`.
- JavaScript: ES modules (`"type": "module"` in `package.json`), `ecmaVersion: "latest"`.
- TypeScript: `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`.
- Path aliases: `@/*` maps to root (via `tsconfig.json` and `jsconfig.json`).

### 1.3 Common

- `.editorconfig` governs basic formatting (utf-8, LF, indent 4, expand-tab).
- `.gitattributes` normalises line endings (`* text=auto`; `.sh` → LF, `.ps1`/`.bat` → CRLF).

---

## 2. Code Style & Formatting

### 2.1 Python — Ruff

All Python code is linted with **[ruff](https://docs.astral.sh/ruff/)** and auto-formatted with **ruff-format**.

| Setting            | Value                                | Source              |
|--------------------|--------------------------------------|---------------------|
| Target version     | `py312`                              | `ruff.toml`         |
| Line length        | **120**                              | `ruff.toml`         |
| Lint rules         | `E` (pycodestyle), `F` (pyflakes)    | `ruff.toml`         |
| Ignored rules      | `E501` (line-too-long), `F401` (unused-import), `F841` (unused-variable) | `ruff.toml` |
| Per-file ignores   | `alembic/versions/*.py`: `E402`, `F401`; `tests/*.py`: `E402` | `ruff.toml` |
| Additional rules (`pyproject.toml`) | `W` (pycodestyle warnings), `I` (isort), `N` (pep8-naming), `UP` (pyupgrade), `B` (flake8-bugbear), `SIM` (flake8-simplify) | `pyproject.toml` |

**Commands:**

```bash
ruff check app --config ruff.toml          # lint
ruff check app --config ruff.toml --fix    # lint + auto-fix
ruff-format app                            # format
```

**Rules of thumb:**
- Prefer readability over brevity — ruff's `SIM` suggestions are advisory, not mandatory.
- `E402` (module-level import not at top) is tolerated in `__init__.py`, lazy-import shims, and `conftest.py` where sys.path manipulation precedes imports.
- Use `# noqa: F401` sparingly — only for re-exports in `__init__.py`.

### 2.2 Frontend — ESLint

Frontend linting uses **[ESLint flat config](https://eslint.org/docs/latest/use/configure/configuration-files)** (`eslint.config.js`).

| Setting              | Value                                        |
|----------------------|----------------------------------------------|
| Base                 | `@eslint/js` recommended                     |
| Plugins              | `eslint-plugin-react`, `eslint-plugin-react-hooks` |
| React version        | `detect`                                     |
| JSX transform        | automatic (`react/react-in-jsx-scope`: off)  |
| `no-unused-vars`     | `warn` (except caught errors)                |
| `react/prop-types`   | off (TypeScript handles types)               |
| Test globals         | `vi` (vitest) readonly                       |
| Threshold            | `--max-warnings 0`                           |

**Command:** `npm run lint` → `eslint . --ext js,jsx --report-unused-disable-directives --max-warnings 0`

### 2.3 No Prettier

There is **no `.prettierrc`** in this project. ruff-format handles Python formatting; ESLint and Next.js conventions handle frontend formatting. Do not introduce Prettier without team consensus.

---

## 3. Naming Conventions

| Language     | Construct           | Convention      | Example                          |
|--------------|---------------------|-----------------|----------------------------------|
| **Python**   | Variables, functions, methods | `snake_case`    | `document_id`, `process_document()` |
| **Python**   | Classes, enums      | `PascalCase`    | `PipelineDocument`, `BlockType`  |
| **Python**   | Constants           | `UPPER_SNAKE`   | `MAX_RETRIES = 3`                |
| **Python**   | Private helpers     | `_leading_underscore` | `_build_hierarchy()`       |
| **Python**   | Module-level "protected" | single `_`    | `_helper.py` (discouraged — prefer sub-packages) |
| **JS/TS**    | Variables, functions, methods | `camelCase` | `getDocument()`, `documentId`  |
| **JS/TS**    | React components    | `PascalCase`    | `DocumentEditor`, `FormatPanel`  |
| **JS/TS**    | Constants           | `UPPER_SNAKE`   | `API_BASE_URL`                   |
| **JS/TS**    | Files (components)  | `PascalCase`    | `DocumentEditor.jsx`             |
| **JS/TS**    | Files (utilities)   | `camelCase`     | `formatCitation.js`              |
| **Python**   | Test functions      | `test_snake`    | `test_document_not_found()`      |
| **JS/TS**    | Test functions      | `camelCase`     | `testDocumentNotFound()`         |
| **Both**     | API route handlers  | descriptive (no convention restriction) | `get_document`, `createDocument` |
| **Both**     | Database columns    | `snake_case`    | `user_id`, `created_at`          |

### 3.1 Python — `Enum` & `StrEnum`

- `BlockType` and similar enums that carry string values use `class BlockType(str, Enum)`.
- Values are **lowercase** (`"body"`, `"title"`, `"heading_1"`) — string comparisons must use the lowercase enum value.

### 3.2 Python — `@staticmethod` vs instance methods

- `@staticmethod` is used selectively (e.g., `_coerce_bool`, `_extract_json`).
- Many "helper" methods (e.g., `_is_likely_affiliation`, `_nlp_classify_fallback`, `_calculate_avg_font_size`) are **instance methods** — do not mark them `@staticmethod` unless the method explicitly has no use for `self`.

---

## 4. Import Style

### 4.1 Absolute imports preferred

Always use absolute imports from the `app` package root:

```python
# ✅ Correct
from app.services.llm_service import generate_with_fallback
from app.models.pipeline_document import PipelineDocument

# ❌ Wrong — relative imports
from ..services.llm_service import generate_with_fallback
```

### 4.2 `from __future__ import annotations`

Every `.py` file in `backend/app/` must start with:

```python
from __future__ import annotations
```

This enables:
- Forward-reference type annotations (no `from __future__` string-quoting needed)
- PEP 604 union syntax (`str | None` instead of `Optional[str]`)
- Lazy evaluation at module load (improves startup time)

### 4.3 Lazy imports for heavy modules

Modules with expensive import chains (Celery, NumPy, SciPy, transformers, torch, PIL, docx, reportlab) must be imported **inside function bodies**, not at module level:

```python
# ✅ Correct — lazy import
def export_to_pdf(document: PipelineDocument) -> bytes:
    from app.pipeline.export.pdf_exporter import PDFExporter
    exporter = PDFExporter()
    return exporter.export(document)

# ❌ Wrong — module-level import of heavy dep
from app.pipeline.export.pdf_exporter import PDFExporter  # don't
```

### 4.4 No wildcard from `app.models`

```python
# ❌ Wrong — adds ~2 minutes to import time
from app.models import *

# ✅ Correct — explicit, targeted imports
from app.models import PipelineDocument, Block, BlockType
```

Wildcard imports from `app.models` are **prohibited** in production code. They are tolerated only in test fixtures that already lazy-import models inside function scope.

### 4.5 Type-only imports

Use `TYPE_CHECKING` guards for imports only needed at type-check time:

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import PipelineDocument
```

### 4.6 Frontend imports

- Use the `@/` path alias (`import { Button } from '@/components/Button'`).
- Prefer named exports for utilities, default exports for page components.
- Barrel files (`index.js`) are acceptable for component directories.

---

## 5. Type Hints

### 5.1 Python — mypy

| Setting                   | Value       | Source        |
|---------------------------|-------------|---------------|
| `python_version`          | `3.12`      | `mypy.ini`    |
| `no_implicit_optional`    | `False`     | `mypy.ini`    |
| `warn_return_any`         | `False`     | `mypy.ini`    |
| `ignore_missing_imports`  | `True`      | `mypy.ini`    |
| `follow_imports`          | `skip`      | `mypy.ini`    |
| Files checked             | `app`       | `mypy.ini`    |

**Rules:**
- **All public API functions require type annotations** on parameters and return values.
- Private helpers (`_`-prefixed) should also be annotated.
- Use `str | None` over `Optional[str]` (PEP 604).
- Use `list[X]` over `List[X]`, `dict[K, V]` over `Dict[K, V]` (requires `from __future__ import annotations`).
- `no_implicit_optional = False` means `x: str = None` is **allowed** (mypy infers `Optional[str]`).
- CI runs mypy with `continue-on-error: true` — violations are warnings, not blockers.

```python
# ✅ Correct — fully annotated
def process_document(doc_id: str, content: str | None = None) -> PipelineDocument:
    ...

# ❌ Wrong — missing annotations
def process_document(doc_id, content=None):
    ...
```

### 5.2 Frontend — TypeScript

- **`strict: true`** in `tsconfig.json` enables `noImplicitAny`, `strictNullChecks`, etc.
- All function parameters and return values must be typed.
- Prefer `interface` over `type` for object shapes (consistent with React ecosystem).
- Use `React.FC` sparingly; type `children` explicitly when needed.
- Run `npm run typecheck` → `tsc --noEmit` before committing.

### 5.3 Frontend — Pyright (supplemental)

Pyright runs in VS Code via `pyrightconfig.json` at `typeCheckingMode: basic`. It provides IDE-level feedback for Python code. CI does not enforce pyright results.

---

## 6. Documentation & Licensing

### 6.1 SPDX Headers

**Every source file** must begin with an SPDX license identifier:

**Python:**
```python
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
```

**JavaScript/JSX/TSX:**
```js
// SPDX-License-Identifier: MIT
// Copyright (c) 2026 ScholarForm AI
```

**YAML/TOML/Config:**
```yaml
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI
```

**Markdown:**
```html
<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->
```

### 6.2 Docstrings

- **Public APIs** (services, routers, pipeline modules) must have a docstring describing purpose, parameters, and return value.
- Use **Google-style** or **reST** docstrings.
- Private helpers (`_`-prefixed) should have a brief inline comment or one-line docstring.

```python
def generate_with_fallback(prompt: str, user_id: str | None = None) -> str:
    """Generate text using a 4-tier fallback chain.

    Tries NVIDIA NIM → Groq → OpenRouter → Ollama in order.
    Returns the first successful generation.

    Args:
        prompt: The input prompt text.
        user_id: Optional user identifier for API key resolution.

    Returns:
        The generated text string.

    Raises:
        LLMUnavailableError: If all providers in the chain fail.
    """
    ...
```

### 6.3 Changelog & Versioning

- Version is canonically defined in `backend/pyproject.toml` (`project.version`).
- `scripts/sync_version.py` propagates it to `frontend/package.json` and `CITATION.cff`.
- Run `python scripts/sync_version.py --check` in pre-commit when version files change.
- See `CHANGELOG.md` for release history (kept via `keepachangelog` format).

---

## 7. Testing Standards

### 7.1 Test Framework

| Layer      | Framework | Config                     |
|------------|-----------|----------------------------|
| Backend    | pytest    | `backend/pytest.ini`       |
| Frontend   | vitest    | `frontend/vitest.config.js` |
| E2E        | Playwright| `frontend/playwright.config.js` |

### 7.2 Backend — pytest

**pytest.ini settings:**
```ini
asyncio_mode = auto       # no @pytest.mark.asyncio needed
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short -p no:langsmith_plugin --timeout=120
```

**Pytest markers** (defined in `pytest.ini`):

| Marker         | Purpose                                                      |
|----------------|--------------------------------------------------------------|
| `integration`  | Requires external services (Redis, GROBID, etc.)            |
| `llm`          | Requires a live LLM (NVIDIA or Ollama)                      |
| `slow`         | Expected to run slowly (> several seconds)                  |
| `service`      | Requires a live external service or heavy runtime dependency |
| `unit`         | Fast unit tests with no external dependencies                |
| `regression`   | Regression tests                                             |
| `database`     | Requires database setup                                      |
| `contract`     | Endpoint contract validation tests                           |
| `pipeline`     | End-to-end pipeline behavior tests                           |
| `rag`          | RAG component tests                                          |
| `ai_quality`   | AI quality evaluation tests                                  |
| `security`     | Security-focused tests                                       |
| `chaos`        | Chaos engineering tests                                      |
| `mutation`     | Mutation tests                                               |
| `property`     | Property-based tests                                         |
| `observability`| Observability tests                                          |
| `performance`  | Performance/load tests                                       |

**Running tests:**
```bash
# Fast unit tests only (no external deps)
pytest tests -m "not integration and not llm and not slow" -x -q

# Specific marker
pytest tests -m security -x -q

# With coverage (may fail — `KeyError: 'pydantic.root_model'` is a known issue)
pytest tests --cov=app --cov-fail-under=70
```

**Important patterns:**

1. **`conftest` autouse fixtures:**
   - `mock_redis` patches global `redis.Redis` with `MagicMock`. Tests that do `isinstance(x, redis.Redis)` must patch `builtins.isinstance` at test time.
   - `reset_rate_limit_state` prevents cross-test contamination from rate limiter state.
   - `reset_health_check_caches` clears cached /health payloads between tests.

2. **`asyncio_mode = auto`** means async test functions are automatically detected — do **not** add `@pytest.mark.asyncio`.

3. **MagicMock rules:**
   - Patching a class method → `patch.object(Cls, "method")` passes `self` to side_effect (3 params).
   - Patching an instance method → `patch.object(instance, "method")` passes 2 params (no `self`).
   - Lazy imports require patching the **source** module, not the consumer.
   - `model_copy` on MagicMock returns a MagicMock — explicitly set `.text` etc. after copy.
   - Two different MagicMock instances are **not** `==` (identity check fallback). Share mock objects when comparing.

4. **Fixture imports:** Model classes imported inside `@pytest.fixture` must be re-imported in test function bodies (goes out of scope).

5. **`sys.modules` contamination:** Any test file that injects mocks into `sys.modules` must save originals and restore them (preferably via `atexit.register`).

6. **`background_tasks.add_task`** does not invoke the callable synchronously — verify with `bt.add_task.assert_called_once_with(...)`.

### 7.3 Frontend — vitest

- Config: `frontend/vitest.config.js` with jsdom environment.
- Setup file: `src/test/setup.js`.
- Test files co-located with components or in `src/test/`.
- E2E tests in `frontend/e2e/` with Playwright.

**Commands:**
```bash
npm run test            # vitest run
npm run test:coverage   # vitest run --coverage
npm run test:e2e        # headless Playwright
npm run test:e2e:headed # Playwright with UI
```

### 7.4 Coverage Threshold

- Backend: **≥70%** (`--cov-fail-under=70`).
- Critical paths (pipeline orchestration, security, auth): **≥90%**.
- Coverage measurement is currently broken with `--cov` (`KeyError: 'pydantic.root_model'`). Tests pass cleanly without `--cov`. CI runs coverage as a separate job with `continue-on-error: true`.

---

## 8. Git Conventions

### 8.1 Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Format:**
```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

**12 allowed types** (defined in `commitlint.config.js`):

| Type       | Usage                                      |
|------------|--------------------------------------------|
| `feat`     | A new feature                              |
| `fix`      | A bug fix                                  |
| `docs`     | Documentation only changes                 |
| `style`    | Code style changes (formatting, lint fixes) |
| `refactor` | Code change that neither fixes nor adds    |
| `perf`     | Performance improvement                    |
| `test`     | Adding or updating tests                   |
| `build`    | Build system or dependency changes         |
| `ci`       | CI/CD configuration changes                |
| `chore`    | Maintenance tasks                          |
| `revert`   | Reverting a previous commit                |
| `security` | Security fixes                             |

**11 allowed scopes** (defined in `commitlint.config.js`):

| Scope       | Area                                       |
|-------------|--------------------------------------------|
| `backend`   | Backend Python code                        |
| `frontend`  | Frontend JavaScript/TypeScript code        |
| `pipeline`  | Document processing pipeline (parsing, formatting, export) |
| `auth`      | Authentication & authorization             |
| `api`       | API route definitions & contracts          |
| `templates` | Document templates & CSL styles            |
| `docs`      | Project documentation                      |
| `ci`        | CI/CD pipeline                             |
| `deps`      | Dependency updates                         |
| `release`   | Release commits                            |
| `docker`    | Docker configuration                       |

**Rules** (enforced by commitlint):
- `scope-empty`: **never** (scope is required).
- `subject-case`: `lower-case`.
- `subject-full-stop`: never (no trailing period).
- `header-max-length`: **100** characters.
- `body-max-line-length`: **100** characters.

**Examples:**
```
feat(backend): add 4-tier LLM fallback chain
fix(pipeline): handle empty reference list in CSL engine
docs(api): document webhook signature verification
security(auth): sanitize JWT claims before role assignment
```

### 8.2 Signed Commits (DCO)

Every commit **must** be signed off to certify compliance with the [Developer Certificate of Origin](DEVELOPER_CERTIFICATE_OF_ORIGIN.md):

```bash
git commit -s          # adds Signed-off-by trailer
git commit --amend -s  # signs the most recent commit
```

The `Signed-off-by` trailer must match the author's real name and email.

### 8.3 Branching Model

- `main` — production-ready, protected, linear history (no merge commits).
- Feature branches: `feat/<short-description>`.
- Fix branches: `fix/<short-description>`.
- All branches are squashed or rebased onto `main` before merging.
- No direct pushes to `main` — only PRs after review.

### 8.4 Pull Requests

- Use the [pull request template](PULL_REQUEST_TEMPLATE.md).
- At least one Core Team member must approve.
- All CI checks must pass.
- Self-review before requesting review.

---

## 9. Pre-commit Hooks

Configured in `.pre-commit-config.yaml` (minimum version: `3.7.0`).

### 9.1 Hook Pipeline (runs in order)

| Hook                    | Source                      | Files                        | Purpose                          |
|-------------------------|-----------------------------|------------------------------|----------------------------------|
| `check-merge-conflict`  | `pre-commit-hooks` v5.0.0   | All                          | Reject merge conflict markers    |
| `check-yaml`            | `pre-commit-hooks` v5.0.0   | All                          | Validate YAML syntax             |
| `end-of-file-fixer`     | `pre-commit-hooks` v5.0.0   | All                          | Ensure trailing newline          |
| `trailing-whitespace`   | `pre-commit-hooks` v5.0.0   | All                          | Trim trailing whitespace         |
| `check-added-large-files`| `pre-commit-hooks` v5.0.0  | All                          | Reject files >500 KB             |
| `check-case-conflict`   | `pre-commit-hooks` v5.0.0   | All                          | Reject case-conflicting names    |
| `check-json`            | `pre-commit-hooks` v5.0.0   | All                          | Validate JSON syntax             |
| `check-toml`            | `pre-commit-hooks` v5.0.0   | All                          | Validate TOML syntax             |
| `check-xml`             | `pre-commit-hooks` v5.0.0   | All                          | Validate XML syntax              |
| `detect-private-key`    | `pre-commit-hooks` v5.0.0   | All                          | Reject accidental key commits    |
| `mixed-line-ending`     | `pre-commit-hooks` v5.0.0   | All                          | Normalize line endings (`--fix=auto`) |
| `fix-byte-order-marker` | `pre-commit-hooks` v5.0.0   | All                          | Remove BOM                       |
| `sort-simple-yaml`      | `pre-commit-hooks` v5.0.0   | All                          | Sort YAML top-level keys         |
| `ruff`                  | `ruff-pre-commit` v0.9.0    | `^backend/`                  | Lint + auto-fix (`--fix`, `--exit-non-zero-on-fix`) |
| `ruff-format`           | `ruff-pre-commit` v0.9.0    | `^backend/`                  | Format via ruff-format           |
| `detect-secrets`        | `detect-secrets` v1.5.0     | All                          | Check against `.secrets.baseline`|
| `version-consistency` (local) | `scripts/sync_version.py` | `backend/pyproject.toml`, `frontend/package.json`, `CITATION.cff` | Ensure version sync |
| `frontend-eslint` (local) | `scripts/run_frontend_eslint_precommit.py` | `^frontend/.*\.(js|jsx|ts|tsx)$` | Run ESLint on staged frontend files |

### 9.2 Installation

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\scripts\setup_precommit.ps1

# Manual
pip install pre-commit
pre-commit install
```

### 9.3 secrets baseline

- Run `detect-secrets scan --baseline .secrets.baseline` to update the baseline after intentionally adding new secret-like strings (e.g., test API keys).
- Never commit actual secrets — even in comments or test fixtures.

---

## 10. Error Handling

### 10.1 Custom Exception Hierarchy

All service-layer code must raise typed exceptions instead of returning `None`/empty collections or swallowing errors.

**Defined in `backend/app/exceptions.py`:**

```
Exception
├── DatabaseUnavailableError     # DB connectivity/server failure
├── DocumentNotFoundError        # Requested document not found (carries doc_id)
├── AuthenticationError          # Authentication failure
├── RateLimitExceededError       # Rate limit exceeded
├── FileStorageError             # File storage operation failure
├── ExternalServiceError         # LLM, GROBID, OCR, or other external service (carries service name)
├── LLMUnavailableError          # All LLM providers in fallback chain failed
├── ConversionError              # Document conversion failure
├── OCRError                     # OCR processing failure
├── CSLEngineError(RuntimeError) # CSL processing failure
```

**Usage pattern:**
```python
def get_document(doc_id: str) -> PipelineDocument:
    result = db.fetch(doc_id)
    if result is None:
        raise DocumentNotFoundError(doc_id=doc_id)
    return result
```

### 10.2 API Envelope Pattern

All API responses use the envelope pattern defined in `backend/app/schemas/api_envelope.py`:

```python
class APIResponse(BaseModel):
    data: Any | None             # Payload on success
    error: APIError | None       # Error on failure
    request_id: str              # Tracing identifier
    timestamp: datetime          # UTC timestamp

class APIError(BaseModel):
    code: str                    # Machine-readable error code
    message: str                 # Human-readable error message
    details: dict | None         # Optional structured details
```

**Helper functions:**
```python
from app.schemas.api_envelope import success_response, error_response

@router.get("/documents/{doc_id}")
async def get_document(doc_id: str, request: Request):
    try:
        doc = await document_service.get(doc_id)
        return success_response(data=doc, request_id=request.state.request_id)
    except DocumentNotFoundError as e:
        return error_response(
            code="DOCUMENT_NOT_FOUND",
            message=str(e),
            request_id=request.state.request_id,
        )
```

### 10.3 Graceful Degradation

- **External service failures** must not crash the request. Wrap calls in try/except and fall back (e.g., LLM 4-tier fallback: NVIDIA NIM → Groq → OpenRouter → Ollama; PDF parser cascade: GROBID → Docling → PyMuPDF → PyPDF2).
- **Feature flags** enable graceful degradation: `DEFAULT_FAST_MODE=true` skips optional AI stages, `USE_LLM_CLASSIFICATION=false` disables LLMClassifier.
- **Circuit breaker** (`app/pipeline/safety/circuit_breaker.py`) wraps external calls with automatic open/close/half-open state transitions. Use `@circuit_breaker` decorator or raise `CircuitBreakerOpenException`.
- **Celery tasks** catch and log errors without crashing the worker.
- **Middleware** (`app/middleware/abuse_detector.py`, `app/middleware/rate_limit.py`) returns 429/403 responses on violation rather than raising unhandled exceptions.
- **Health checks** (`/health`, `/ready`) serve stale cached responses if live checks fail.

### 10.4 Logging

- Use `structlog` (structured logging) over raw `logging`.
- Include `request_id` in every log line within request scope.
- Never log secrets, API keys, or raw document content that may contain PII.
- Use `logging_context.py` (`MetricsManager`) for request-scoped metrics.

---

## 11. Security & Secrets

### 11.1 Secrets Management

- **No hardcoded secrets** — ever. Not in code, tests, fixtures, or examples.
- Sensitive values go in `backend/.env` (gitignored) or Render environment variables.
- API keys are stored encrypted in the `user_api_keys` database table.
- `detect-secrets` with `.secrets.baseline` runs in pre-commit to catch accidental commits.

### 11.2 Secure Coding

- **Input validation:** All API inputs are validated by Pydantic schemas.
- **Output sanitization:** LLM outputs pass through `guard_llm_output` from `app/pipeline/safety/llm_validator.py`.
- **Rate limiting:** Multi-tier rate limiter at middleware level (`app/middleware/rate_limit.py`, `app/middleware/tier_rate_limit.py`).
- **CORS:** Restricted origin list in `app/middleware/cors.py`.
- **CSRF:** Token-based protection in `app/middleware/csrf.py`.
- **Auth:** JWT verification via `app/security/jwks_verifier.py`.
- **RBAC:** Role-based access control in `app/middleware/rbac.py`.
- **SSRF protection:** Outbound request URLs validated against private IP ranges.
- **File upload:** Virus scanning, size limits, type validation.
- **CI/CD:** Dependency vulnerability scanning, `npm audit` on frontend.

---

## 12. File Structure & Encoding

### 12.1 `.editorconfig`

```ini
[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
insert_final_newline = true
trim_trailing_whitespace = true

[*.{yml,yaml,json,toml}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false

[Makefile]
indent_style = tab
```

### 12.2 `.gitattributes`

- `* text=auto` — Git auto-detects text files.
- Shell scripts (`.sh`): `eol=lf` enforced.
- PowerShell (`.ps1`), Batch (`.bat`): `eol=crlf` enforced.
- Binary types (`.png`, `.jpg`, `.docx`, `.pdf`, `.zip` etc.): `binary`.
- Generated/minified files (`.min.js`, `package-lock.json`): `linguist-generated=true`.
- `CHANGELOG.md`: `merge=union` (avoid merge conflicts on changelog).

### 12.3 Directory Layout

```
backend/
  app/                    # FastAPI application
    routers/              # API routes
    services/             # Business logic (27 services)
    pipeline/             # Document processing pipeline
    tasks/                # Celery background tasks
    models/               # Pydantic + SQLAlchemy models
    schemas/              # Request/response schemas
    middleware/            # ASGI middleware
    security/             # Auth, JWT, CSP
    config/               # App configuration
  tests/                  # Pytest test suite
  db/                     # Alembic migrations + semantic store

frontend/
  src/
    app/                  # Next.js 16 App Router pages
    components/           # React components
    context/              # React context providers
    hooks/                # Custom React hooks
    services/             # API client services
    lib/                  # Utility functions
    test/                 # Test setup and utilities
  e2e/                    # Playwright E2E tests
```

### 12.4 Router Prefixing (Backend)

All sub-routers under `v1_router` (`prefix="/api/v1"`) must **not** define their own `prefix`. Prefixes are set exclusively via `include_router(sub, prefix="/subpath")` in `app/routers/v1/__init__.py`.

```python
# ✅ Correct — no prefix on sub-router
router = APIRouter()  # no prefix= argument

@router.get("/documents")
async def list_documents():
    ...

# The parent __init__.py does:
# v1_router.include_router(router, prefix="/documents")
```

---

## 13. Enterprise Refactoring Conventions

### Exception Hierarchy
- All business exceptions must inherit from `ScholarFormError` (in `app/exceptions.py`)
- DO NOT raise `HTTPException` from services — use domain exceptions with `http_status`
- Global exception handler in `main.py` maps domain exceptions to HTTP responses

### Service Layer
- Services must NOT import pipeline modules directly — use service facades
- Service facades live in `app/services/` and provide async methods with full type annotations
- Each service facade has a single responsibility (e.g., `GenerationService`, not `AIService`)

### Pipeline Architecture
- Pipeline stages implement `StageContract` protocol
- Stages are stateless — all state lives in `PipelineDocument`
- Each stage has `execute()`, `validate()`, and `rollback()` methods
- Orchestrator coordinates stages but contains no stage logic

### Imports
- No lazy imports (imports inside function bodies) — use proper module restructuring instead
- No circular imports — extract shared dependencies to `app/common/` if needed
- Import at module level only

---

## Appendix A — Quick Reference

### A.1 CI Pipeline (order)

```
backend-ci.yml:
  1. ruff (E9, F63, F7, F82)
  2. mypy (continue-on-error)
  3. pytest (skip integration & slow)

frontend-ci.yml:
  1. npm ci
  2. eslint
  3. vitest
  4. next build
  5. Lighthouse CI
  6. Playwright e2e
```

### A.2 Key Environment Flags

| Variable                     | Default | Purpose                          |
|------------------------------|---------|----------------------------------|
| `LOW_MEMORY_MODE`            | `true`  | Reduce memory usage              |
| `PRELOAD_AI_MODELS`          | `false` | Preload AI models on startup     |
| `DEFAULT_FAST_MODE`          | `true`  | Skip optional AI pipeline stages |
| `USE_LLM_CLASSIFICATION` | `false` | Enable LLMClassifier classifier        |
| `TESTING`                    | —       | Set to `1` in test mode (short-circuits lifespan) |

### A.3 Useful Commands

```bash
# Backend lint/format
ruff check app --config ruff.toml
ruff check app --config ruff.toml --fix
ruff-format app

# Backend types
mypy --config-file mypy.ini app

# Backend tests
pytest tests -m "not integration and not llm and not slow" -x -q

# Frontend
npm run dev           # next dev --turbopack
npm run lint          # eslint --max-warnings 0
npm run test          # vitest run
npm run typecheck     # tsc --noEmit

# Git
git commit -s         # sign off commit
npm run commit        # interactive commitlint (if installed)
```

---

*Maintainers: Keep this document in sync whenever a linter rule, test marker, commit type, or infrastructure convention changes. Last updated: 2026-07-16.*
