# AMF Backend

RESTful API server for the Automated Manuscript Formatter. Provides manuscript formatting, validation, and preview generation powered by FastAPI.

## Installation

```bash
pip install amf-backend
```

## Quick Start

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/format` | Format a manuscript |
| POST | `/api/v1/validate` | Validate manuscript structure |
| POST | `/api/v1/preview` | Generate HTML preview |
| GET | `/api/v1/styles` | List all citation styles |
| GET | `/health` | Health check |

See [full documentation](https://amf.dev/docs) for details.
