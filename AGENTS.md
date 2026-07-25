# AI Agents Development Guide

## Overview

AMF supports AI agent integration through its API and CLI. This guide explains how AI coding agents can effectively work with the AMF codebase.

## Repository Map

### Key Entry Points

```
automated-manuscript-formatter/
├── backend/app/main.py          # API entry point
├── backend/app/api/routes.py    # All API endpoints
├── backend/app/services/        # Core business logic
├── cli/amf/main.py              # CLI entry point
├── sdk/amf_sdk/client.py        # SDK entry point
├── frontend/src/app/            # Frontend pages
└── docs/                        # Documentation
```

### Service Dependencies

```
routes.py ──→ formatter.py ──→ python-docx
routes.py ──→ parser.py
routes.py ──→ validator.py
routes.py ──→ style_registry.py
```

## Common Agent Tasks

### Adding a New Citation Style

1. Add style config in `backend/app/services/style_registry.py`
2. Add any special formatting in `backend/app/services/formatter.py`
3. Register style in validator if special rules needed
4. Add frontend display in `frontend/src/lib/constants.ts`
5. Write tests in `backend/tests/test_formatter.py`

### Adding a New API Endpoint

1. Define request/response models in `backend/app/api/models.py`
2. Add route handler in `backend/app/api/routes.py`
3. Implement service logic if needed
4. Add tests in `backend/tests/test_api.py`
5. Update API docs in `docs/docs/api/reference.md`

### Adding a New CLI Command

1. Create command file in `cli/amf/commands/`
2. Register command in `cli/amf/main.py`
3. Add tests in `cli/tests/test_cli.py`
4. Update CLI docs in `docs/docs/cli/reference.md`

## Important Conventions

- Python type hints required on all public functions
- Pydantic v2 for all data validation
- Use pathlib for file paths (cross-platform)
- Rich library for CLI terminal output
- Conventional Commits for commit messages
- Ruff for Python formatting

## Agent-Optimized Documentation

- `ARCHITECTURE.md` — System architecture overview
- `SYSTEM_DESIGN.md` — Design decisions and patterns
- `API_REFERENCE.md` — Complete API documentation
- `CLI_REFERENCE.md` — CLI command reference
- `SDK_GUIDE.md` — Python SDK usage
- `CONFIGURATION.md` — Configuration reference
- `TESTING.md` — Test guide
- `ERROR_CODES.md` — Error code reference
