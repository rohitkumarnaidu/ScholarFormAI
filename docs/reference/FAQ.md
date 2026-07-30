<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Frequently Asked Questions

## General

### What is ScholarForm AI?

ScholarForm AI is an open-source platform that automatically formats academic manuscripts to journal submission guidelines. It supports 17+ journal templates, AI-powered manuscript generation, and multi-document synthesis.

### Is ScholarForm AI free?

Yes. The core platform is open source (MIT License). You can self-host it for free. A hosted cloud version with additional features (higher API rate limits, priority processing, storage) is planned.

### Do I need an API key to use it?

Locally, no. In production, you can use the built-in Supabase auth or provide your own LLM API keys (NVIDIA, Groq, Ollama).

## Technical

### What Python version do I need?

**Python 3.12.x only.**

### What Node.js version do I need?

Node.js 20+ (LTS). The frontend uses Next.js 16 (App Router), which requires Node 20+.

### Can I use Vite instead of Next.js?

No. The frontend is built on Next.js 16 App Router. Vite is not supported. See [ADR 010](docs/adr/010-nextjs-app-router.md) for reasoning.

### Do I need GROBID?

No. ScholarForm uses a 3-tier PDF parsing fallback: GROBID (if enabled, Docker ~1.5GB RAM) → Docling → PyMuPDF. GROBID is optional and disabled by default in low-memory mode.

### Can I use this without GPU?

Yes. The AI pipeline works CPU-only. LLM inference runs via API (NVIDIA NIM, Groq, Ollama) — no local GPU required.

## Features

### What journal templates are available?

17+ templates including: IEEE, APA, ACM, Springer, Elsevier, Nature, Harvard, Chicago, MLA, Vancouver, Numeric, Modern Blue/Gold/Red, Resume, Portfolio, and None (passthrough).

### Can I create my own template?

Yes. Create a `template.docx` with Jinja2 placeholders, a `contract.yaml` for validation, and optionally a `styles.csl` for citations. See [Template Creation Guide](docs/template_creation.md).

### Does it support citations?

Yes. Citation formatting uses CSL (Citation Style Language). Any of 10,000+ CSL styles can be added. Currently ships with 10 built-in styles.

### Can I format PDFs?

PDF input is supported via GROBID/Docling/PyMuPDF pipeline. Output is DOCX (with PDF export planned).

## Deployment

### How do I deploy to production?

See the [Deployment Guide](docs/Deployment.md). The recommended stack is Vercel (frontend) + Render (backend) + Supabase (database).

### Can I deploy on my own server?

Yes. The full stack runs via Docker Compose. See `backend/docker/docker-compose.yml`. No external service dependencies required beyond PostgreSQL and Redis.

### What is the memory requirement for the backend?

The Render free tier (512MB RAM) is sufficient with `LOW_MEMORY_MODE=true`. GROBID requires ~1.5GB RAM if enabled.

## Contributing

### How do I contribute?

See [CONTRIBUTING.md](CONTRIBUTING.md). All contributions require DCO sign-off (`git commit -s`).

### Do I need to sign a CLA?

No. ScholarForm AI uses the [Developer Certificate of Origin](../community/DEVELOPER_CERTIFICATE_OF_ORIGIN.md) (DCO) instead of a CLA. Just sign off your commits with `git commit -s`.

### What license does the project use?

MIT License. See [LICENSE](LICENSE).

## Troubleshooting

### The backend won't start

- Ensure Python 3.12.x (not 3.11, not 3.13+)
- Run `pip install -r requirements.txt` in the `backend/` directory
- Check `.env` has required variables (copy from `.env.example`)
- Port 8000 may be in use: `uvicorn app.main:app --reload --port 8001`

### Tests fail with import errors

```bash
# Ensure you're using Python 3.12.x
python --version
# Ensure virtual environment is activated
pip install -r requirements-dev.txt
# Run fast tests only
pytest tests -m "not integration and not llm and not contract" -x -q
```

### Frontend can't reach the backend

- Ensure backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env` (defaults to `http://localhost:8000`)
- CORS: backend allows `http://localhost:3000` by default

---

*Last updated: July 2026*
