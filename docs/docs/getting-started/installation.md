# Installation

## Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend development)
- Docker (optional, for containerized deployment)

## Docker (Recommended)

```bash
git clone https://github.com/amf/automated-manuscript-formatter.git
cd automated-manuscript-formatter
docker compose up -d
```

## Manual Installation

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm ci
```

### CLI

```bash
pip install amf-cli
# Or install locally:
cd cli && pip install -e .
```

### SDK

```bash
pip install amf-sdk
# Or install locally:
cd sdk && pip install -e .
```

## Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check CLI
amf --version

# List styles
curl http://localhost:8000/api/v1/styles
```
