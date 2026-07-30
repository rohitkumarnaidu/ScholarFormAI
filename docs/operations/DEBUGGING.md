<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Debugging Guide

## Quick Diagnostics

```bash
# 1. Check Python version (must be 3.12.x)
python --version

# 2. Check Node version (must be 20+)
node --version

# 3. Verify backend can start
cd backend
uvicorn app.main:app --reload --port 8000

# 4. Check health endpoint
curl http://localhost:8000/api/v1/health/live

# 5. Verify frontend builds
cd frontend
npm run build
```

## Backend Debugging

### Server Won't Start

**Symptom:** `uvicorn` exits immediately or port conflicts

```bash
# Check port in use
netstat -ano | findstr :8000    # Windows
# lsof -i :8000                 # macOS/Linux

# Check Python version
python --version
# Must output 3.12.x — not 3.11, not 3.13+

# Check all dependencies installed
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Try with more verbose logging
uvicorn app.main:app --reload --port 8000 --log-level debug
```

### Import Errors

```bash
# Ensure virtual environment is activated and Python 3.12
python -c "import app.main; print('OK')"

# If circular imports: check app/pipeline/*.py for cross-module deps
# If module not found: pip list | grep <module_name>
```

### Database Connection Errors

```bash
# Check Supabase connection
curl -X GET "$SUPABASE_URL/rest/v1/" \
  -H "apikey: $SUPABASE_SERVICE_KEY"

# Run Alembic migrations
alembic upgrade head
alembic current  # Check current state
```

### API Returns 500

```bash
# Enable debug mode in .env
DEBUG=true

# Check server logs for traceback (Uvicorn prints to stdout)

# Isolate the endpoint
curl -v http://localhost:8000/api/v1/health
```

## Frontend Debugging

### Build Fails

```bash
# Clear Next.js cache
cd frontend
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue  # Windows
# rm -rf .next                                                     # macOS/Linux
npm run build

# Check for TypeScript errors
npx tsc --noEmit

# Stuck on module resolution
npm install --legacy-peer-deps
```

### API Calls Not Working

```bash
# Check NEXT_PUBLIC_API_URL
echo $env:NEXT_PUBLIC_API_URL                    # Windows
# echo $NEXT_PUBLIC_API_URL                       # macOS/Linux

# Should be http://localhost:8000 (dev) or https://api.scholarform.ai (prod)

# Browser dev tools → Network tab → check:
#   - Request URL
#   - Response status
#   - CORS errors (missing Access-Control-Allow-Origin)
```

### Hydration Errors

Next.js hydration errors usually mean server/client HTML mismatch:

1. Check for `typeof window` or `useEffect` blocks that render different content
2. Wrap browser-only code in `useEffect` or dynamic imports with `ssr: false`
3. Check for missing `suppressHydrationWarning` on theme elements

## Pipeline Debugging

### Document Formatting Fails

Enable verbose logging:

```bash
# Set in .env
DEBUG=true
LOG_LEVEL=DEBUG
```

Check the formatting job status:

```bash
curl http://localhost:8000/api/v1/documents/{job_id}/status
# Returns: { "status": "failed", "error": "...", "stage": "parsing" }
```

### LLM Calls Fail

```bash
# Check LLM provider status
curl http://localhost:8000/api/v1/health
# Check "services" object for LLM provider health

# Test LLM directly
curl -X POST http://localhost:8000/api/v1/generator/sessions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test", "model": "nvidia"}'
```

### SSE Events Not Streaming

1. Check if Celery worker is running: check Render dashboard or `celery -A app.tasks.celery_tasks status`
2. Check Redis connection: `redis-cli ping` should return `PONG`
3. SSE events require backend to be accessible from frontend (no firewalls)

## Docker Debugging

```bash
# Check container logs
docker compose logs -f api
docker compose logs -f worker

# Shell into container
docker compose exec api bash

# Check resource usage
docker stats
```

## Common Error Codes

| Code | Meaning | Fix |
|------|---------|-----|
| `E001` | Invalid file type | Upload .docx or .pdf only |
| `E002` | File too large | Max 50MB per upload |
| `E003` | Virus detected | Scan failed; check file |
| `E004` | Template not found | Use valid template name |
| `E005` | LLM provider unreachable | Check fallback chain |
| `E006` | Database timeout | Check Supabase status |
| `E007` | Redis connection failed | Check Redis URL in .env |
| `E008` | Celery worker unavailable | Start worker process |

---

*Last updated: July 2026*
