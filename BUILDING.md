<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Building ScholarForm AI From Source

## Prerequisites

- Python 3.12.x (3.11 causes pytest import collisions)
- Node.js 20+ (LTS recommended)
- npm 10+
- Git

## Quick Build

```bash
# Clone
git clone https://github.com/scholarform/scholarform.git
cd scholarform

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify
ruff check app && echo "Backend lint OK"
mypy app && echo "Backend types OK" || echo "Type check issues (non-blocking)"
pytest tests -m "not integration and not llm" -x -q

# Frontend
cd ../frontend
npm install
npm run build
npm test
npm run lint

# Build production bundle
npm run build
```

## Docker Build

```bash
# Backend
docker build -t scholarform-api:latest -f backend/Dockerfile backend/

# Frontend
docker build -t scholarform-ui:latest -f frontend/Dockerfile frontend/
```

See [docker-compose.yml](backend/docker/docker-compose.yml) for the full service stack (GROBID + support services).

## Development Build

For development with hot reload:

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev    # next dev --turbopack
```

## Build Outputs

| Target | Output | Location |
|--------|--------|----------|
| Backend package | Python package | `backend/dist/` |
| Frontend (dev) | Dev server | `http://localhost:3000` |
| Frontend (prod) | Static export | `frontend/.next/` |
| Docker (API) | Docker image | `scholarform-api:latest` |
| Docker (UI) | Docker image | `scholarform-ui:latest` |

## CI Build

Our CI pipeline builds and tests every PR and push to `main`:

- Backend CI: `.github/workflows/backend-ci.yml`
- Frontend CI: `.github/workflows/frontend-ci.yml`
- Security: `.github/workflows/security.yml`

---

*Last updated: June 2026*
