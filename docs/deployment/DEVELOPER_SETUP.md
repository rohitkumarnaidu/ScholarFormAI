# ScholarForm AI — Developer Setup Guide

> **Step-by-step setup.** For onboarding workflow, see [docs/DEVELOPER_ONBOARDING.md](../developer-guide/DEVELOPER_ONBOARDING.md). For build instructions, see [BUILDING.md](BUILDING.md).

---

## Prerequisites

| Tool | Version | Notes |
| ------ | --------- | ------- |
| Python | 3.12.x | 3.11 causes pytest import collisions; 3.13+ untested |
| Node.js | 20+ (LTS) | 18.17+ minimum for Next.js 16 |
| npm | 10+ | Comes with Node.js |
| Redis | 7.x | Optional — needed for Celery + realtime features |
| Docker | 24+ | Optional — for GROBID and microservices |
| Git | Latest | Required for version control |

---

## 1. Clone

```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd ScholarFormAI
```

---

## 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify
python --version  # Must be 3.12.x
ruff check app    # Should pass
```

---

## 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Verify
npm run lint
npm run build
```

---

## 4. Environment Variables

### Backend (`backend/.env`)

Copy from template:

```bash
cp backend/.env.example backend/.env
```

Minimum required variables:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
SECRET_KEY=your-random-secret-key
LOW_MEMORY_MODE=true
DEFAULT_FAST_MODE=true
```

Optional AI keys (for LLM features):

```env
NVIDIA_API_KEY=nvapi-...
GROQ_API_KEY=gsk_...
REDIS_URL=redis://localhost:6379
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...
```

> All frontend env vars must be prefixed with `NEXT_PUBLIC_`.

---

## 5. Run Locally

### Terminal 1 — Backend

```bash
cd backend
.venv\Scripts\activate   # or source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

API docs: <http://localhost:8000/docs>

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

App: <http://localhost:3000>

### Verify

```bash
curl http://localhost:8000/api/v1/health/live
# → {"status":"ok","services":{...}}
```

---

## 6. Docker Development

### Start Services (GROBID + support)

```bash
cd backend/docker
docker-compose up -d
```

### Build Images

```bash
# Backend API
docker build -t scholarform-api:latest -f backend/Dockerfile backend/

# Frontend
docker build -t scholarform-ui:latest -f frontend/Dockerfile frontend/
```

---

## 7. Testing Setup

```bash
# Backend (fast tests, no services needed)
cd backend
pytest tests -m "not integration and not llm and not contract" -x -q

# Frontend
cd frontend
npm test

# Pre-commit hooks
pip install pre-commit
pre-commit install
```

---

## 8. Common Issues

| Problem | Solution |
| --------- | ---------- |
| `Python 3.11` — pytest import errors | Install Python 3.12.x |
| `ModuleNotFoundError` | `pip install -r requirements-dev.txt` |
| CORS errors | Check `ALLOWED_ORIGINS` in backend `.env` |
| Frontend build fails | `rm -rf node_modules && npm install` |
| Port 8000 in use | `uvicorn app.main:app --reload --port 8001` |
| Supabase connection refused | Check `SUPABASE_URL` in `.env` |
| Redis not available | Set `REDIS_URL` or disable Celery features |

---

## 9. Next Steps

1. Read [CONTRIBUTING.md](../../CONTRIBUTING.md) for PR workflow
2. Read [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) for system overview
3. Read [docs/DEVELOPER_ONBOARDING.md](../developer-guide/DEVELOPER_ONBOARDING.md) for full onboarding
4. Browse [examples/](examples/) for API usage samples

---

*Last updated: July 2026*
