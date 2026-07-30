# ScholarForm AI — Troubleshooting Guide

> **Quick reference.** For the full troubleshooting guide (user-facing issues), see [docs/troubleshooting.md](docs/troubleshooting.md).

---

## Backend Issues

### "Python 3.11 detected" or import errors
```bash
python --version   # Must be 3.12.x
```
Fix: Install Python 3.12.x and recreate your virtual environment.

### `ModuleNotFoundError` on startup
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```
Fix: Ensure virtual environment is activated and all deps installed.

### Backend won't start — port in use
```bash
uvicorn app.main:app --reload --port 8001
```

### `pytest` tests fail at collection
- Cause: Python 3.11 import collision
- Fix: `python --version` must show 3.12.x

### Supabase connection errors
- Check `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` in `backend/.env`
- Verify Supabase project is active

### Redis connection refused
- Start Redis locally, or set `REDIS_URL` to empty to run without Celery
- Redis is optional for basic formatting

---

## Frontend Issues

### Build fails
```bash
rm -rf node_modules
npm install
npm run build
```

### CORS errors in browser dev tools
- Ensure `NEXT_PUBLIC_API_URL=http://localhost:8000` matches backend port
- Check `ALLOWED_ORIGINS` in backend `.env` includes `http://localhost:3000`

### Frontend can't reach backend
- Verify backend is running: `curl http://localhost:8000/api/v1/health/live`
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`

### E2E tests fail
- Ensure backend is running
- Run `npm run test:e2e:headed` to see browser interaction
- Check Playwright trace in `test-results/`

### `@testing-library/dom` not found
```bash
npm install @testing-library/dom --save-dev
```

---

## Processing Issues

### Upload fails — "Invalid file type"
Supported formats: DOCX, PDF, LaTeX, Markdown, HTML, TXT

### Upload fails — "File too large"
Maximum file size: 50 MB. Compress images or split appendices.

### Job stuck on "RUNNING"
1. Refresh the page
2. Check backend logs
3. Try re-uploading

### Formatting fails — try with "None" template
Sometimes template mismatches cause failures. Use `None` template to diagnose, then re-run with target template.

### Agent session hangs
- Check LLM provider status (NVIDIA NIM → Groq → Ollama fallback chain)
- Try a shorter prompt
- Restart the session

### Synthesis SSE disconnects
- Reduce number of PDFs (max 6)
- Ensure each PDF is under 50 MB
- Retry the session

---

## Deployment Issues

### Render out of memory
Set `LOW_MEMORY_MODE=true` and `PRELOAD_AI_MODELS=false` in environment.

### GROBID won't start
GROBID requires ~1.5GB RAM. On low-memory instances, it auto-disables. The fallback chain (Docling → PyMuPDF) will handle PDFs.

### Vercel deployment fails
- Check Next.js build logs
- Verify all `NEXT_PUBLIC_*` env vars are set in Vercel project settings

---

## Getting Help

| Channel | Purpose |
|---------|---------|
| [GitHub Issues](https://github.com/rohitkumarnaidu/ScholarFormAI/issues) | Bug reports, feature requests |
| [GitHub Discussions](https://github.com/rohitkumarnaidu/ScholarFormAI/discussions) | Q&A, community help |
| [FAQ](../reference/FAQ.md) | Frequently asked questions |
| [SUPPORT](../../SUPPORT.md) | Support channels and SLAs |
| [docs/troubleshooting.md](../troubleshooting.md) | User-facing troubleshooting |

---

*Last updated: July 2026*
