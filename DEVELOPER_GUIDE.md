# Developer Guide

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- Docker (optional)

### Clone and Install

```bash
git clone https://github.com/amf/automated-manuscript-formatter.git
cd automated-manuscript-formatter

# Install all dependencies
make install

# Setup pre-commit hooks
make install-dev
```

## Development Workflow

### Start Dev Servers

```bash
# Terminal 1: Backend API
make dev-backend

# Terminal 2: Frontend
make dev-frontend

# Terminal 3: Documentation
make dev-docs
```

### Code Quality

```bash
# Lint all code
make lint

# Format all code
make format

# Run all tests
make test

# Run specific tests
cd backend && pytest tests/test_api.py -v
cd frontend && npm test -- --watch
```

### Build

```bash
# Build all packages
make build

# Build specific
cd backend && python setup.py sdist bdist_wheel
cd frontend && npm run build
```

## Project Architecture

```
backend/app/
├── main.py              # FastAPI application entry
├── api/
│   ├── routes.py        # API endpoints
│   └── models.py        # Request/response schemas
├── core/
│   ├── config.py        # Configuration
│   └── exceptions.py    # Custom exceptions
├── services/
│   ├── formatter.py     # DOCX formatting engine
│   ├── parser.py        # Manuscript parsing
│   ├── validator.py     # Validation logic
│   └── style_registry.py # Built-in styles
└── schemas/
    ├── manuscript.py    # Domain models
    └── formatting.py    # Formatting models
```

## Adding a New Citation Style

1. Add style definition in `backend/app/services/style_registry.py`
2. Add formatting rules in `backend/app/services/formatter.py` if needed
3. Add validation rules in `backend/app/services/validator.py` if needed
4. Update `frontend/src/lib/constants.ts` with style info
5. Add tests in `backend/tests/test_formatter.py`

## Docker Development

```bash
# Build and start all services
docker compose up -d

# Rebuild specific service
docker compose build backend
docker compose up -d backend

# View logs
docker compose logs -f frontend
```

## Testing Guidelines

- Unit tests for all services
- Integration tests for API endpoints
- Snapshot tests for frontend components
- Aim for minimum 80% code coverage
- Tests should be fast and isolated

## Documentation

- All public functions need docstrings
- Update API docs when endpoints change
- Update CLI docs when commands change
- Run `make docs` to verify documentation builds
