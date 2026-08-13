# Developer Guide

Welcome to the ScholarFormAI Developer Guide! This document helps new contributors get the project running locally and explains the architecture.

## System Architecture

ScholarFormAI consists of three main components:
1. **API Server:** A FastAPI (Python) backend that handles authentication, job queuing, and API endpoints.
2. **Worker Nodes:** Celery workers that parse OOXML `.docx` files, apply AI-driven formatting rules, and construct new `.docx` binaries.
3. **Frontend Dashboard:** A React-based dashboard for users to manage templates and API keys.

## Setting Up the Development Environment

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose

### 2. Clone the Repository
```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd ScholarFormAI
```

### 3. Infrastructure
Start the required background services (PostgreSQL, Redis):
```bash
docker-compose up -d db redis
```

### 4. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## Running Tests

Ensure all tests pass before submitting a Pull Request.

```bash
# Backend tests
pytest tests/

# Frontend tests
npm run test
```

## Cross References
- [Style Guide](STYLE_GUIDE.md)
- [API Reference](../api/API_REFERENCE.md)
- [Plugin Guide](../sdk/PLUGIN_GUIDE.md)
