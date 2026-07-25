# Automated Manuscript Formatter (AMF)

> **Enterprise-grade formatting of academic manuscripts into professionally styled DOCX documents.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Node.js 20+](https://img.shields.io/badge/Node-20%2B-green)](https://nodejs.org/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Vision

Academic formatting is a tedious, error-prone bottleneck in the research workflow. AMF eliminates this by providing a single, unified platform where researchers write their content and get perfectly formatted manuscripts in any major citation style — APA, MLA, Chicago, IEEE, and more.

## Features

- **Multi-Format Input** — Write in Markdown, LaTeX, or plain text
- **9+ Citation Styles** — APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, Vancouver, Turabian, ACS, AMA
- **Real-Time Preview** — Live HTML preview before downloading
- **Validation Engine** — Automatic structure, citation, and style compliance checks
- **Enterprise API** — RESTful API with SDK support for Python
- **CLI Tool** — Format manuscripts directly from the terminal
- **Docker Support** — One-command deployment with Docker Compose
- **Web UI** — Modern, responsive interface built with Next.js
- **Extensible** — Plugin architecture for custom styles and templates

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Web UI     │────▶│  API Gateway │────▶│  Formatter   │
│  (Next.js)  │     │  (FastAPI)   │     │  (python-docx)│
└─────────────┘     └──────────────┘     └──────────────┘
                           │                      │
┌─────────────┐           │                      │
│  CLI Tool   │──────────▶│                      │
│  (Click)    │           │                      │
└─────────────┘           │                      │
                           │                      │
┌─────────────┐           │              ┌───────┴────────┐
│  Python SDK │──────────▶│              │  Style Registry │
│  (httpx)    │           │              │  (9 built-in)   │
└─────────────┘           │              └────────────────┘
```

## Quick Start

### Using the Web UI

```bash
docker compose up
# Open http://localhost:3000
```

### Using the CLI

```bash
pip install amf-cli
amf init my-paper
amf format -i my-paper/manuscript.md -s apa
```

### Using the API

```bash
curl -X POST http://localhost:8000/api/v1/format \
  -H "Content-Type: application/json" \
  -d '{
    "manuscript": {"title": "My Paper", "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Hello world"}]}]},
    "style_id": "apa"
  }'
```

### Using the SDK

```python
from amf_sdk import AMFClient

client = AMFClient()
styles = client.get_styles()
result = client.format_manuscript(manuscript, style="mla")
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+ (for frontend development)
- Docker (optional, for containerized deployment)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

### CLI

```bash
cd cli
pip install -e .
amf --help
```

### SDK

```bash
cd sdk
pip install -e .
```

## Supported Styles

| Style | Version | Discipline | Citation Format | Abstract Required |
|-------|---------|------------|----------------|:---:|
| APA | 7th | Social Sciences, Psychology | Author-Year | ✓ |
| MLA | 9th | Humanities, Literature | Author-Page | ✓ |
| Chicago | 17th | History, Arts | Notes-Bibliography | ✓ |
| IEEE | 2023 | Engineering, CS | Numbered | ✗ |
| Harvard | 2023 | Multi-discipline (UK/AU) | Author-Date | ✗ |
| Vancouver | 2023 | Biomedical | Numbered | ✓ |
| Turabian | 9th | Student Papers | Notes-Bibliography | ✓ |
| ACS | 2023 | Chemistry | Numbered | ✗ |
| AMA | 11th | Medical Research | Numbered | ✓ |

## Configuration

Configuration is managed via environment variables (prefixed with `AMF_`) or a `.env` file:

```env
AMF_ENVIRONMENT=development
AMF_DEBUG=true
AMF_LOG_LEVEL=info
AMF_MAX_UPLOAD_SIZE=10485760
AMF_DEFAULT_STYLE=apa
AMF_API_PREFIX=/api/v1
```

## Docker

```bash
# Build and start all services
docker compose up -d

# Build specific service
docker compose build backend

# View logs
docker compose logs -f
```

## Development

```bash
# Install all dependencies
make install

# Run all tests
make test

# Lint all code
make lint

# Format all code
make format

# Start dev servers
make dev-backend   # API at localhost:8000
make dev-frontend  # UI at localhost:3000
make dev-docs      # Docs at localhost:8008
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/format` | Format a manuscript |
| POST | `/api/v1/validate` | Validate manuscript structure |
| POST | `/api/v1/preview` | Generate HTML preview |
| GET | `/api/v1/styles` | List all styles |
| GET | `/api/v1/styles/{id}` | Get style details |
| GET | `/health` | Health check |

## Roadmap

- [x] Core formatting engine with 9 citation styles
- [x] RESTful API with FastAPI
- [x] Web UI with Next.js
- [x] CLI tool
- [x] Python SDK
- [ ] PDF output support
- [ ] Custom style creator
- [ ] Batch processing mode
- [ ] Overleaf/LaTeX integration
- [ ] Zotero/Mendeley reference import
- [ ] Plugin marketplace
- [ ] AI-powered citation fixing
- [ ] Collaborative editing

## Community

- **GitHub Issues** — Bug reports, feature requests
- **Discussions** — Q&A, ideas, show and tell
- **Contributing** — See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Code of Conduct** — See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Security** — See [SECURITY.md](SECURITY.md)

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
