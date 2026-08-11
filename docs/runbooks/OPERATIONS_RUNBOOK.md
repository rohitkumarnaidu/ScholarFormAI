<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Operations Runbook
description: Comprehensive operations guide covering service management, monitoring, incident response, and recovery
sidebar_position: 40
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Operations Runbook

**RTO:** 4 hours | **RPO:** 1 hour | **Availability SLO:** 99.9%

> **See also:** [Disaster Recovery](../operations/DISASTER_RECOVERY.md), [Production Readiness](../reports/PRODUCTION_READINESS_CHECKLIST.md), [SLO Definitions](../SLO_DEFINITIONS.md), [Runbooks](runbooks/)

---

## Table of Contents

1. [Service Overview](#1-service-overview)
2. [Routine Operations](#2-routine-operations)
3. [Monitoring](#3-monitoring)
4. [Incident Response](#4-incident-response)
5. [Common Procedures](#5-common-procedures)
6. [Recovery Procedures](#6-recovery-procedures)
7. [Backup and Restore](#7-backup-and-restore)
8. [Performance Tuning](#8-performance-tuning)
9. [Security Procedures](#9-security-procedures)
10. [Emergency Contacts](#10-emergency-contacts)

---

## 1. Service Overview

### Architecture

```
                         ┌──────────────────────┐
                         │   Frontend (Next.js)  │
                         │   scholarform.ai      │
                         │   Render / Vercel     │
                         └─────────┬────────────┘
                                   │ HTTPS / WSS
                         ┌─────────▼────────────┐
                         │  Backend (FastAPI)    │
                         │  uvicorn (1-4 workers)│
                         │  Render Web Service   │
                         └──┬──────┬──────┬─────┘
                            │      │      │
              ┌─────────────┘      │      └──────────────┐
              ▼                    ▼                      ▼
   ┌──────────────────┐  ┌──────────────┐  ┌─────────────────────┐
   │  PostgreSQL       │  │  Redis 7     │  │  Celery Workers     │
   │  Supabase (PITR)  │  │  Cache/Queue │  │  interactive + batch│
   │  Continuous B/U   │  │  allkeys-lru │  │  Render Worker      │
   └──────────────────┘  └──────────────┘  └─────────┬───────────┘
                                                      │
                    ┌─────────────────────────────────┤
                    ▼              ▼              ▼           ▼
           ┌────────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐
           │  GROBID     │ │ Docling  │ │  OCR   │ │  ClamAV      │
           │  0.8.0      │ │ Service  │ │ Service│ │  Malware     │
           │  4GB heap   │ └──────────┘ └────────┘ │  Scanner     │
           └────────────┘                           └──────────────┘
                    ▼              ▼              ▼           ▼
           ┌────────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐
           │  LLMPDFParser     │ │ LLMClassifier │ │ Docx   │ │  Ollama /    │
           │  Parser     │ │ Classif.│ │ Conv.  │ │  Local LLM   │
           └────────────┘ └──────────┘ └────────┘ └──────────────┘
```

### Service Dependencies

| Service | Port | Criticality | Fallback Strategy |
| --------- | ------ | ------------- | ------------------- |
| **PostgreSQL (Supabase)** | 5432 | **Critical** | PITR continuous backup; Supabase managed |
| **Redis** | 6379 | **High** | Ephemeral; cache rebuilds automatically |
| **GROBID** | 8070 | **High** | Docling → PyMuPDF → PyPDF2 cascade |
| **Docling** | - | Medium | PyMuPDF fallback |
| **OCR** | - | Medium | Backend-only processing fallback |
| **ClamAV** | 3310 | Medium | AV scanning can be bypassed in degraded mode |
| **Celery Workers** | - | **High** | Interactive + batch queues; synchronous fallback |
| **LLM Providers** | - | **High** | NVIDIA NIM → Groq → OpenRouter → Ollama (4-tier) |
| **LLMPDFParser** | - | Low | Disabled by default (ENABLE_LLM_PDF_PARSER=false) |
| **LLMClassifier** | - | Low | NLP classification fallback (USE_LLM_CLASSIFICATION=false by default) |

### Environment

- **Platform:** Render (Web Service + Celery Worker + Redis)
- **Python:** 3.12.2
- **Frontend:** Next.js 16 (App Router) — `npm run dev` uses Turbopack
- **Deployment:** Git push → auto-deploy via Render

---

## 2. Routine Operations

### Starting / Stopping Services

#### Backend (Local Development)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Backend (Docker Compose — Full Stack)

```bash
cd backend/docker
docker compose up -d                 # Start all services
docker compose up -d grobid redis    # Start specific services
docker compose down                  # Stop all services
docker compose logs -f --tail=100   # Tail logs
```

#### Celery Workers

```bash
# Interactive queue (4 concurrent tasks)
celery -A app.tasks.celery_tasks worker -Q interactive -c 4 --loglevel=info

# Batch queue (2 concurrent tasks)
celery -A app.tasks.celery_tasks worker -Q batch -c 2 --loglevel=info

# Both queues from single worker
celery -A app.tasks.celery_tasks worker -Q interactive,batch -c 2 --loglevel=info --prefetch-multiplier=1
```

#### Celery Beat (Scheduled Tasks)

```bash
celery -A app.tasks.celery_tasks beat --loglevel=info
# Scheduled: cleanup-stranded-uploads-daily at 03:00 UTC
```

#### Production (Render)

- Backend auto-deploys from `main` branch
- Manual deploy: `render deploy --service scholarform-backend`
- Rollback: `render rollback --service scholarform-backend`

### Health Checks

| Endpoint | Purpose | Expected Status |
| ---------- | --------- | ---------------- |
| `GET /health` | Liveness probe | Always 200 (returns component status) |
| `GET /ready` | Readiness probe | 200 when all critical deps healthy, 503 otherwise |
| `GET /api/v1/health/live` | K8s/Docker liveness | 200 |
| `GET /api/v1/health/ready` | Strict readiness | 503 if any dependency degraded |
| `GET /metrics` | Prometheus scrape | 200, Prometheus-formatted metrics |

```bash
# Quick health check
curl -s https://api.scholarform.ai/health | jq .
curl -s -o /dev/null -w "%{http_code}" https://api.scholarform.ai/ready

# Readiness with full dependency status
curl -s https://api.scholarform.ai/ready | jq '.checks'
```

Health and readiness payloads are cached with a configurable TTL (default 15s, set via `READINESS_CACHE_TTL_SECONDS` / `HEALTH_CACHE_TTL_SECONDS`). Cache can be invalidated programmatically via `invalidate_readiness_cache()` / `invalidate_health_cache()`.

### Log Inspection

```bash
# Render logs (production)
render logs --service scholarform-backend --tail 100
render logs --service scholarform-celery-worker --tail 100

# Docker logs (local)
docker compose logs -f scholarform-backend
docker compose logs -f scholarform-celery-worker-interactive
docker compose logs -f scholarform-celery-worker-batch
docker compose logs -f scholarform-grobid

# Local dev logs
Get-Content backend/app.log -Tail 100 -Wait   # Windows PowerShell
tail -f backend/app.log                        # WSL/Git Bash
```

Structured JSON logging is enabled in production (`ENABLE_STRUCTURED_LOGGING=true`). Each log entry includes:

- `request_id` — Correlation ID from `RequestIdMiddleware`
- `timestamp` — ISO 8601 UTC
- `level` — Log severity
- `component` — Module name
- `event` — Structured event name

### Configuration Inspection

```bash
# View current effective settings (via debug endpoint)
# Settings are loaded from .env + environment via pydantic-settings
# Key env files: backend/.env (local), Render Dashboard (production)

# Validate encryption key is present
if (-not $env:ENCRYPTION_KEY) { Write-Warning "ENCRYPTION_KEY not set!" }

# Verify Redis connectivity
redis-cli -u $env:REDIS_URL ping
```

---

## 3. Monitoring

### Grafana Dashboard Walkthrough

**Dashboard:** `scholarform-production` (UID: `scholarform-production`)

**Panel Layout (3 rows, 24-column grid):**

#### Row 1: API Health (y=0)

| Panel | Type | Position | Query | Thresholds |
|-------|------|----------|-------|------------|
| **API Request Rate** | Time series | x=0, w=12 | `rate(http_requests_total{job="scholarform"}[5m])` | — |
| **Error Rate** | Time series | x=12, w=12 | `rate(5xx[5m]) / rate(total[5m]) * 100` | Green <1%, Yellow 1-5%, Red >5% |

#### Row 2: Latency (y=8)

| Panel | Type | Position | Query | Thresholds |
|-------|------|----------|-------|------------|
| **Response Latency (p50, p95, p99)** | Time series | x=0, w=24 | `histogram_quantile(0.50/0.95/0.99, rate(http_request_duration_seconds_bucket[5m]))` | — |

#### Row 3: System Status (y=16)

| Panel | Type | Position | Query | Thresholds |
| ------- | ------ | ---------- | ------- | ------------ |
| **Active Users** | Stat | x=0, w=6 | `count(scholarform_active_users)` | — |
| **Pipeline Processing Rate** | Stat | x=6, w=6 | `rate(scholarform_pipeline_documents_processed_total[5m])` | — |
| **API Key Usage Rate** | Time series | x=12, w=12 | `rate(scholarform_api_key_requests_total[5m])` | — |

#### Row 3 (continued): Infrastructure (y=20)

| Panel | Type | Position | Query | Thresholds |
|-------|------|----------|-------|------------|
| **DB Connection Pool** | Gauge | x=0, w=6 | `scholarform_db_pool_active_connections` | Green <15, Yellow 15-18, Red >18 (max=20) |
| **Redis Memory Usage** | Gauge | x=6, w=6 | `redis_memory_used_bytes / redis_memory_max_bytes * 100` | Green <75%, Yellow 75-90%, Red >90% |

#### Row 4: Reliability & Queues (y=24)

| Panel | Type | Position | Query | Thresholds |
|-------|------|----------|-------|------------|
| **Error Budget Remaining (30d)** | Gauge | x=0, w=12 | `(1 - (30d 5xx / 30d total)) / 0.999 * 100` | Red <25%, Yellow 25-50%, Green >50% |
| **Celery Queue Depth** | Time series | x=12, w=12 | `scholarform_celery_queue_depth{queue="interactive"}` + batch | Interactive >100 triggers warning |

### Prometheus Alert Interpretation

| Alert | Severity | Condition | Runbook | Action |
| ------- | ---------- | ----------- | --------- | -------- |
| `ScholarFormServiceDown` | **CRITICAL** | `up{job="scholarform"} == 0` for 2m | [service-down.md](service-down.md) | Service unreachable — check Render dashboard |
| `ScholarFormHighErrorRate` | WARNING | 5xx rate > 5% for 5m | [high-error-rate.md](high-error-rate.md) | Recent deploy? DB connectivity? |
| `ScholarFormHighLatency` | WARNING | p95 > 5s for 5m | [high-latency.md](high-latency.md) | External dep slow? Worker backlog? |
| `ScholarFormDBPoolExhausted` | **CRITICAL** | Active > 18 for 2m | [db-pool-exhausted.md](runbooks/db-pool-exhausted.md) | Connection leak or traffic spike |
| `ScholarFormRedisMemoryHigh` | WARNING | Memory > 90% for 5m | [redis-memory.md](runbooks/redis-memory.md) | Check cache TTLs; flush if needed |
| `ScholarFormQueueBacklog` | WARNING | Interactive depth > 100 for 10m | [queue-backlog.md](runbooks/queue-backlog.md) | Scale workers or investigate stuck task |
| `ScholarFormRateLimitSpike` | INFO | Rate limit hits > 10/s for 5m | — | Possible abuse or misconfigured client |
| `ScholarFormDiskSpaceLow` | **CRITICAL** | Available < 10% for 10m | [disk-space.md](runbooks/disk-space.md) | Clean uploads; verify retention policy |

### Prometheus Metrics Exposed

All metrics served at `GET /metrics` via `prometheus_fastapi_instrumentator`. Custom metrics:

| Metric | Type | Description |
| -------- | ------ | ------------- |
| `scholarform_db_pool_active_connections` | Gauge | Current active DB connections |
| `scholarform_celery_queue_depth{queue="interactive\|batch"}` | Gauge | Number of pending Celery tasks |
| `scholarform_active_users` | Gauge | Currently active user sessions |
| `scholarform_api_key_requests_total{provider="..."}` | Counter | API key usage by provider |
| `scholarform_api_key_rate_limited_total` | Counter | Rate-limited API key requests |
| `scholarform_pipeline_documents_processed_total` | Counter | Pipeline throughput |
| `http_requests_total{method,path,status}` | Counter | Standard HTTP metrics |
| `http_request_duration_seconds_bucket` | Histogram | Request latency distribution |

### Alerting Infrastructure

- **Alert rules:** `deploy/prometheus/error_budget.yml` — evaluated every 15s
- **Grafana:** Dashboard at `https://grafana.scholarform.ai/d/scholarform-production`
- **Error tracking:** Handled via Prometheus metrics and structured logging (Sentry removed)
- **Lighthouse CI:** Core Web Vitals (LCP <2.5s, FID <100ms, CLS <0.1)

---

## 4. Incident Response

### Severity Levels

| Severity | Definition | Response Time | Examples |
| ---------- | ----------- | --------------- | ---------- |
| **P0 (Critical)** | Complete service outage or data loss | < 5 minutes | Service down, DB unavailable, data corruption |
| **P1 (High)** | Major feature broken, degraded for users | < 15 minutes | Error rate >5%, p95 latency >5s, pipeline broken |
| **P2 (Medium)** | Partial degradation, non-critical broken | < 1 hour | Error rate >1%, single endpoint slow |
| **P3 (Low)** | Cosmetic issue, minor performance blip | < 4 hours | Low-severity alert, non-functional feature |
| **P4 (Info)** | Informational, no user impact | Next business day | Rate limit spike, unusual but non-blocking pattern |

### Incident Response Workflow

```
DETECTION → TRIAGE → MITIGATION → RESOLUTION → POSTMORTEM
  (alert)   (5 min)   (<30 min)    (<4 hr)     (<48 hr)
```

#### Detection

- Prometheus alerts via `error_budget.yml`
- Sentry error threshold breaches
- Grafana dashboard anomaly observation
- User-reported issues (via support)

#### Triage (first 5 minutes)

1. **Acknowledge** the alert (respond in PagerDuty / incident channel)
2. **Assess severity** using the matrix above
3. **Declare incident** in `#incidents` Slack channel with:
   - `INCIDENT-###` identifier
   - Current severity level
   - Affected service(s)
   - Link to relevant Grafana dashboard
4. **Assemble response team** based on escalation matrix

#### Mitigation (first 30 minutes)

1. Apply the relevant playbook from `docs/runbooks/`
2. Check Render dashboard for recent deploys
3. Verify dependency health (Supabase, Redis, GROBID, LLM providers)
4. If bad deploy: rollback immediately (`render rollback --service scholarform-backend`)
5. If dependency failure: activate fallback chain or restart service
6. If data issue: freeze writes, assess corruption scope

#### Resolution

- Verify through health checks and dashboards
- Confirm error budget impact
- Update incident status in Slack
- Notify affected users (if any)

#### Postmorten (within 48 hours for P0/P1)

- Follow [Postmortem Template](../POSTMORTEM_TEMPLATE.md)
- Document root cause, timeline, action items
- Update runbooks with lessons learned
- Track action items in project management

### Escalation Paths

```
Level 0: On-Call Engineer (PagerDuty rotation)
         └─ Can rollback, restart services, scale workers
Level 1: Backend Lead
         └─ Can deploy hotfixes, modify pipeline code
Level 2: DevOps Lead
         └─ Can modify infrastructure, scale resources
Level 3: Engineering Director
         └─ Can make policy decisions, declare major incident
```

#### Escalation by Alert Type

| Alert Type | Level 0 | Level 1 | Level 2 |
| ----------- | --------- | --------- | --------- |
| Service Down | On-call engineer | Backend lead | DevOps lead |
| Error Rate | On-call engineer | Backend lead | — |
| High Latency | On-call engineer | Performance owner | DevOps lead |
| DB Pool Exhausted | On-call engineer | Backend lead | DevOps lead |
| Redis Memory | On-call engineer | — | DevOps lead |
| Queue Backlog | On-call engineer | — | DevOps lead |
| Disk Space | On-call engineer | — | DevOps lead |
| Security Incident | On-call engineer | Security lead | Engineering Director |

---

## 5. Common Procedures

### Deployment

#### Standard Deploy (Render — auto-deploy)

```bash
# Simply push to main branch — Render auto-deploys
git push origin main

# Monitor deployment
render logs --service scholarform-backend --tail 50
```

#### Manual Deploy

```bash
render deploy --service scholarform-backend
# or for frontend
npm run build && render deploy --service scholarform-frontend
```

#### Rollback

```bash
# Rollback backend to previous version
render rollback --service scholarform-backend

# Rollback frontend
render rollback --service scholarform-frontend
```

#### Deployment Checklist

- [ ] Tests passing on CI (pytest, vitest, Playwright)
- [ ] Lint/type checks passing (ruff, mypy, eslint)
- [ ] No unresolved `detect-secrets` warnings
- [ ] Version synced (`python scripts/sync_version.py`)
- [ ] Migrations created for schema changes (`alembic upgrade head`)
- [ ] `.env.example` updated if new variables added
- [ ] Monitor dashboards for 10 minutes post-deploy

### Configuration Changes

1. **Local:** Edit `backend/.env` — changes take effect on restart
2. **Production:** Update via Render Dashboard → Environment → Edit
3. **Secret rotation:** Use `ENCRYPTION_KEY` for encrypted fields; stored in Render env vars
4. **New settings:** Add field to appropriate sub-class in `backend/app/config/settings.py`

```bash
# After config change, verify
curl -s https://api.scholarform.ai/health | jq .
```

**Important:** `ENCRYPTION_KEY` must be preserved across restarts — encrypted data (API keys, tokens) will be lost if changed.

### Database Migrations

```bash
cd backend

# Apply pending migrations
alembic upgrade head

# Create new migration (autogenerate)
alembic revision --autogenerate -m "description_of_change"

# View migration history
alembic history

# Rollback one migration
alembic downgrade -1
```

**Note:** Alembic reads `SUPABASE_DB_URL` from environment at runtime (configured in `env.py`). The URL in `alembic.ini` is a placeholder only.

The Docker entrypoint runs `alembic upgrade head` automatically before starting uvicorn.

### Cache Clearing

#### Redis Cache Flush (Selective)

```bash
# Flush all Redis data (all keys)
redis-cli -u $env:REDIS_URL FLUSHALL

# Flush current database only
redis-cli -u $env:REDIS_URL FLUSHDB

# List all keys matching pattern
redis-cli -u $env:REDIS_URL KEYS "llm_cache:*"
# Delete specific key pattern
redis-cli -u $env:REDIS_URL DEL "llm_cache:*"
```

**Note:** Redis is ephemeral — flushing only resets rate limit counters and caches. All data rebuilds automatically.

#### Health Check Cache Invalidation

Health check cache TTL is 15s by default. To force refresh:

```bash
curl -s "https://api.scholarform.ai/ready?force=1"
```

#### File Cleanup

```bash
# Manual trigger (via Celery)
celery -A app.tasks.celery_tasks call batch.cleanup_uploads --kwargs='{"upload_dir":"uploads"}'

# Automatic: runs daily at 03:00 UTC via Celery Beat
# Retention: 30 days (configurable via RETENTION_DAYS)
```

### Celery Worker Scaling

```bash
# Scale interactive workers (Render)
render scale --service scholarform-celery-worker --num-instances 2

# Adjust per-worker concurrency via env var
WORKER_CONCURRENCY=4   # default: 2

# Check worker status
celery -A app.tasks.celery_tasks status

# Inspect active tasks
celery -A app.tasks.celery_tasks inspect active

# View registered tasks
celery -A app.tasks.celery_tasks inspect registered
```

---

## 6. Recovery Procedures

### Service Restart

```bash
# Restart backend via Render
render restart --service scholarform-backend

# Restart Celery worker
render restart --service scholarform-celery-worker

# Restart via Docker (local)
docker compose restart scholarform-backend
docker compose restart scholarform-celery-worker-interactive
docker compose restart scholarform-celery-worker-batch
docker compose restart scholarform-grobid
docker compose restart scholarform-redis

# Backend startup sequence (automated):
# 1. Sentry init (3s timeout)
# 2. Startup validation (15s timeout) — checks env keys, Redis, Supabase
# 3. Interrupted job reset — marks PROCESSING docs as FAILED
# 4. GROBID probe (25s timeout, 3 attempts per endpoint) — degrades gracefully
# 5. AI model pre-load (optional, skipped if LOW_MEMORY_MODE or PRELOAD_AI_MODELS=false)
# 6. Enhancement capabilities refresh (8s timeout)
# 7. Preview CSS preload (5s timeout)
# 8. Celery queue depth monitor starts (30s interval)

# Each startup step has an independent timeout — the app always starts even if
# individual steps fail (degraded mode).
```

### Database Recovery

#### Supabase Managed (PITR) — Preferred

```bash
# 1. Navigate to Supabase Dashboard → Database → Backups
# 2. Select restore point (any timestamp within 7-day retention)
# 3. Click "Restore" — wait 5-15 minutes
# 4. Verify with:
python backend/scripts/verify_backup.py
python backend/scripts/verify_migration.py
# 5. Restart backend
render restart --service scholarform-backend
```

#### Manual PostgreSQL Dump Restore

```bash
# Restore from custom format dump
pg_restore --dbname=$SUPABASE_DB_URL --clean --no-owner backup_20260716_030000.dump

# Restore from plain SQL dump
psql $SUPABASE_DB_URL < schema_backup.sql
```

#### Check Supabase Status

```bash
# External status page
curl -s https://status.supabase.com
# Or API endpoint
curl -s https://status.supabase.com/api/v1/components
```

### Redis Flush / Recovery

Redis data is **ephemeral**. No data loss — only cache and rate limit counters are affected.

```bash
# After any Redis issue:
redis-cli -u $env:REDIS_URL FLUSHALL

# Verify reconnect
redis-cli -u $env:REDIS_URL ping
# → PONG

# Cache will warm naturally as requests come in.
# Rate limit counters reset — acceptable.
```

### ChromaDB Restore

> ChromaDB is used for RAG (semantic search) in the document pipeline.

```bash
# ChromaDB data is stored in the configured persistence directory.
# Determined by settings (CHROMA_PERSIST_DIR or similar).

# 1. Verify ChromaDB data directory exists
Test-Path -LiteralPath "backend/db/semantic_store"

# 2. Restore from backup
Copy-Item -Recurse -Path "backups/chromadb_20260716/*" -Destination "backend/db/semantic_store/"

# 3. Verify RAG engine loads
python -c "from app.pipeline.intelligence.rag_engine import get_rag_engine; rag = get_rag_engine(); print('RAG OK:', rag.knowledge_base.count() if hasattr(rag.knowledge_base, 'count') else 'loaded')"

# 4. If no backup exists, rebuild by re-embedding guidelines:
python scripts/rebuild_semantic_store.py
```

### Pipeline Recovery

```bash
# Check for stuck/interrupted jobs
# On startup, documents with status=PROCESSING are automatically marked as FAILED.
# Manual check:
python -c "
import asyncio
from app.services.document_service import DocumentService
docs = asyncio.run(DocumentService.get_documents_by_status('PROCESSING'))
print(f'Stuck documents: {len(docs)}')
for d in docs:
    print(f'  - {d[\"id\"]}: {d.get(\"current_stage\", \"unknown\")}')
"

# To manually fail a stuck job:
python -c "
import asyncio
from app.services.document_service import DocumentService
asyncio.run(DocumentService.update_document('DOC-ID', {'status': 'FAILED', 'error_message': 'Manually failed by operator'}))
"
```

### Recovery Post-Checks

After any recovery action, verify:

```bash
# 1. Liveness
curl -s https://api.scholarform.ai/health | jq '.status'

# 2. Readiness  
curl -s -o /dev/null -w "%{http_code}" https://api.scholarform.ai/ready

# 3. Database health (from readiness payload)
curl -s https://api.scholarform.ai/ready | jq '.checks.database'

# 4. Pipeline functional
curl -s https://api.scholarform.ai/ready | jq '.checks.ai_models, .checks.grobid'

# 5. Run smoke tests
cd backend
pytest tests/test_smoke.py -v --no-cov
```

---

## 7. Backup and Restore

### Database Backup

| Method | Frequency | Retention | Type |
| -------- | ----------- | ----------- | ------ |
| Supabase PITR | Continuous | 7 days | Automated |
| Manual `pg_dump` | Weekly | 30 days | On-demand |
| Schema-only dump | Weekly | Permanent | Version-controlled |

```bash
# Manual pg_dump
pg_dump $SUPABASE_DB_URL --format=custom --file=backup_$(date +%Y%m%d_%H%M%S).dump

# Schema-only (version-controlled)
pg_dump $SUPABASE_DB_URL --schema-only --file=schema_$(date +%Y%m%d).sql
```

### File Storage Backup (Supabase)

```bash
# List storage buckets
supabase storage ls --project-ref YOUR_PROJECT_REF

# Download all files recursively
supabase storage download --project-ref YOUR_PROJECT_REF --recursive / uploads_backup/
```

### Local Upload Files Backup

```bash
# Upload files directory (retention: 30 days by default)
robocopy backend/uploads backups/uploads_$(date +%Y%m%d) /E /COPY:DAT     # Windows
rsync -av backend/uploads/ backups/uploads_$(date +%Y%m%d)/               # WSL/Git Bash
```

### ChromaDB Backup

```bash
# ChromaDB semantic store
Copy-Item -Recurse -Path "backend/db/semantic_store" -Destination "backups/chromadb_$(date +%Y%m%d)"    # Windows
cp -r backend/db/semantic_store backups/chromadb_$(date +%Y%m%d)                                          # Git Bash
```

### Configuration Backup

```bash
# Environment variables (encrypted)
gpg --symmetric --cipher-algo AES256 backend/.env
# Store .env.gpg in secure vault (1Password / LastPass)

# Render env vars — manually export from Render Dashboard
```

### Git Backup

Code and templates (`backend/app/templates/`) are version-controlled in GitHub. All settings, migrations, and configuration are in the repository (except secrets).

### Backup Verification

```bash
# Verify database backup integrity
python backend/scripts/verify_backup.py

# Verify migration state
python backend/scripts/verify_migration.py

# Verify restore works (in staging)
pg_restore --dbname=$STAGING_DB_URL --clean --no-owner backup_file.dump
```

### Backup Schedule

| Task | Frequency | Responsible | Automation |
| ------ | ----------- | ------------- | ------------ |
| Supabase PITR | Continuous | Supabase | Automatic |
| Manual DB dump (weekly) | Sunday 02:00 UTC | DevOps | Cron script |
| File storage sync | Daily 04:00 UTC | DevOps | Celery beat |
| ChromaDB snapshot | Weekly | DevOps | Manual |
| Env var backup | On change | DevOps | Manual |
| Backup verification | Weekly (Monday) | CI/CD | `verify_backup.py` |
| Retention cleanup | Daily 03:00 UTC | Celery | `batch.cleanup_uploads` |

---

## 8. Performance Tuning

### Connection Pools

#### Database Connection Pool

- **Max pool size:** 20 connections (Supabase managed)
- **Warning threshold:** 15 active connections (yellow on Grafana)
- **Critical threshold:** 18 active connections (red + alert)
- **Alert:** `ScholarFormDBPoolExhausted` if active > 18 for 2 minutes

**Tuning:**

- If hitting pool limits, check for connection leaks (unclosed DB sessions)
- Increase pool size via Supabase Dashboard if needed (plan upgrade may be required)
- Ensure `async` DB operations properly release connections
- Consider implementing connection pooling at the application level

#### Celery Worker Concurrency

```bash
# Current defaults:
WEB_CONCURRENCY=1     # uvicorn workers (Render: $PORT single process)
WORKER_CONCURRENCY=2  # Celery tasks per worker

# Tuning guidelines:
# - interactive queue: 4 workers per instance for I/O-bound tasks
# - batch queue: 2 workers per instance for CPU-bound tasks
# - Prefetch multiplier: 1 (prevents worker hoarding)
```

**When to scale:**

- **Interactive queue depth** > 100 for > 10 minutes → increase workers
- **Batch queue backlog** > 50 → increase batch workers
- **CPU > 80%** consistently → reduce concurrency, add more instances
- **Memory > 80%** → reduce concurrency, enable `LOW_MEMORY_MODE=true`

### Cache TTL Configuration

All TTLs in `CacheSettings` (settings.cache):

| Setting | Default | Recommendation |
| --------- | --------- | ---------------- |
| `LLM_CACHE_TTL_SECONDS` | 3600 (1h) | Reduce to 1800 for rapidly changing prompts; increase to 7200 for stable |
| `READINESS_CACHE_TTL_SECONDS` | 15 | Keep low (5-15s) for accurate health status |
| `HEALTH_CACHE_TTL_SECONDS` | 15 | Keep low (5-15s) |
| `CSL_SEARCH_CACHE_TTL_SECONDS` | 300 (5min) | Increase to 600 if citation DB is stable |
| `CSL_FETCH_CACHE_TTL_SECONDS` | 1800 (30min) | Increase to 3600 for production |
| `GENERATOR_SESSION_CACHE_TTL_SECONDS` | 2.0s | Keep low for real-time sessions |
| `GENERATOR_DOCUMENT_CACHE_TTL_SECONDS` | 2.0s | Keep low |
| `DOCUMENT_STATUS_CACHE_TTL_SECONDS` | 1.0s | Keep very low for status polling |

**High-traffic tuning:**

1. Increase `LLM_CACHE_TTL_SECONDS` to 7200+ to reduce LLM provider calls
2. Increase `CSL_FETCH_CACHE_TTL_SECONDS` to 3600+ to reduce CrossRef API calls
3. Ensure `REDIS_ENABLED=true` for distributed caching

**Low-memory tuning:**

1. Set `LOW_MEMORY_MODE=true` — skips AI model pre-loading
2. Set `PRELOAD_AI_MODELS=false` — models load on-demand
3. Set `RAG_USE_TRANSFORMERS=false` — use API-based embeddings
4. Reduce Celery concurrency

### Redis Performance

- **Eviction policy:** `allkeys-lru` (Render) — evicts least recently used keys
- **Persistence:** AOF (append-only file) in Docker; ephemeral on Render (free tier)
- **Memory monitoring:** Alert at > 90% usage
- **Key patterns:** `llm_cache:*`, `csl_cache:*`, `session:*`, `rate_limit:*`

```bash
# Redis memory info
redis-cli -u $env:REDIS_URL INFO memory

# Key count
redis-cli -u $env:REDIS_URL DBSIZE

# Biggest keys
redis-cli -u $env:REDIS_URL --bigkeys
```

### Circuit Breaker Tuning

```bash
EXTERNAL_CIRCUIT_BREAKER_ENABLED=true
EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD=3    # Open after 3 consecutive failures
EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS=60        # Half-open attempt after 60s
```

**Tuning guidelines:**

- **Latency-sensitive endpoints:** Lower threshold to 2, lower reset to 30s
- **Transient failure tolerance:** Increase threshold to 5, increase reset to 120s
- **External API calls:** Keep defaults (3/60)
- **Database:** Consider disabling circuit breaker — use connection pool instead

### LLM Provider Fallback Tiers

```
NVIDIA NIM (primary) → Groq (fallback) → OpenRouter (fallback) → Ollama (local fallback)
```

Configure API keys in environment:

- `NVIDIA_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`

**Provider timeout:** 15s (`LLM_PROVIDER_TIMEOUT_SECONDS`)

---

## 9. Security Procedures

### Key Rotation

#### Encryption Key Rotation

The `ENCRYPTION_KEY` is used for encrypting user API keys stored in the `user_api_keys` table.

```bash
# 1. Generate new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Update ENCRYPTION_KEY in Render Dashboard → Environment
# 3. Restart backend: render restart --service scholarform-backend

# WARNING: Rotating ENCRYPTION_KEY invalidates all existing encrypted data.
# All user API keys will be lost and must be re-entered by users.
# Plan rotation during maintenance window and communicate to users.
```

#### LLM Provider API Key Rotation

```bash
# 1. Update key in Render Dashboard → Environment
#    e.g., NVIDIA_API_KEY, GROQ_API_KEY, OPENAI_API_KEY
# 2. No restart needed — keys are read at request time (lazy-loaded)
# 3. Verify with health check
curl -s https://api.scholarform.ai/api/v1/health/ready | jq '.checks.llm_status'
```

#### Supabase Service Role Key

```bash
# 1. Generate new key from Supabase Dashboard → Settings → API
# 2. Update SUPABASE_SERVICE_ROLE_KEY in Render Dashboard
# 3. Restart backend
```

### Certificate Renewal

TLS termination is handled by Render at the edge. No manual certificate management required.

- **Render:** Automatic Let's Encrypt certificate renewal
- **Custom domain:** Configured in Render Dashboard → Settings → Custom Domain
- **Verification:** `curl -vI https://scholarform.ai` — check certificate expiry

### Audit Log Review

The system logs all HTTP write operations (POST, PUT, DELETE, PATCH) through the `audit_log_service`.

```bash
# Audit logs are captured via MonitoringMiddleware
# Each audit entry includes:
# - request_id (correlation ID)
# - method, path, status_code
# - user_id (if authenticated)
# - timestamp

# View recent audit entries
curl -s https://api.scholarform.ai/api/v1/audit/logs?limit=50 | jq '.'

# Review for suspicious patterns (high-velocity writes, unusual paths)
# Alerting: ScholarFormRateLimitSpike triggered at >10 rate-limited req/s
```

**Audit retention:** Configured via audit log service settings. Review access weekly for P0/P1 events.

### Security Incident Response

| Incident Type | Response | Escalation |
| --------------- | ---------- | ------------ |
| Suspected breach | Isolate affected service, revoke keys, initiate incident | Security lead + Engineering Director |
| DDoS / abuse | Rate limiting engages automatically; may need IP block | DevOps lead |
| Vulnerable dependency | Apply patch, run CI security scan | Backend lead |
| Exposed credentials | Rotate keys immediately, review audit logs | Security lead |

### Additional Security Measures

- **CORS:** Restricted to configured origins (`CORS_ORIGINS`)
- **HTTPS forced:** `FORCE_HTTPS=true` in production (via `HTTPSRedirectMiddleware` + `HSTSMiddleware`)
- **Max body size:** 60MB (`MaxBodySizeMiddleware`)
- **Rate limiting:** SlowAPI (global); TierRateLimitMiddleware (per-user); per-endpoint limits
- **CSRF:** Token-based protection via `CSRFMiddleware`
- **Security headers:** CSP, X-Frame-Options, X-Content-Type-Options via `SecurityHeadersMiddleware`
- **Request validation:** Structured error responses with `RequestValidationError` handler
- **SSRF prevention:** URL validation blocks private IP ranges (RFC 1918, loopback, link-local)
- **ClamAV:** Malware scanning for uploaded files
- **Webhook security:** HMAC signature verification, replay prevention, origin validation
- **Abuse detection:** Rate-based and content-based pattern detection

---

## 10. Emergency Contacts

### On-Call Rotation

| Role | Contact Method | Coverage |
| ------ | --------------- | ---------- |
| Primary On-Call | PagerDuty | 24/7 |
| Secondary On-Call | PagerDuty (escalation) | 24/7 |
| Engineering Lead | Slack / Email | Business hours + escalation |
| DevOps Lead | Slack / Email | Business hours + escalation |

### Escalation Matrix

| Role | Name | Email | Slack | Phone |
| ------ | ------ | ------- | ------- | ------- |
| On-Call Engineer | PagerDuty rotation | Via PagerDuty | @oncall | Via PagerDuty |
| Engineering Lead | [TBD] | [TBD] | @eng-lead | [TBD] |
| DevOps Lead | [TBD] | [TBD] | @devops-lead | [TBD] |
| Security Lead | [TBD] | [TBD] | @security-lead | [TBD] |
| Frontend Lead | [TBD] | [TBD] | @fe-lead | [TBD] |

### Vendor Emergency Contacts

| Vendor | Contact | Method | SLA |
| -------- | --------- | -------- | ----- |
| Supabase | <support@supabase.com> | Dashboard → Help | Pro: 4hr response |
| Render | <support@render.com> | Dashboard → Support | 2hr response (Pro) |
| GitHub | <support@github.com> | Premium: 4hr | Enterprise: 1hr |

### Communication Channels

| Channel | Purpose | Link |
| --------- | --------- | ------ |
| `#incidents` | Active incident coordination | Slack |
| `#oncall` | On-call handoff / quiet hours | Slack |
| `#engineering` | General engineering communication | Slack |
| Status page | Public service status | `https://status.scholarform.ai` |
| Postmortems | Incident analysis archive | `docs/postmortems/` |

### Post-Incident Recovery Checklist

- [ ] All services responding to health checks
- [ ] Database integrity verified
- [ ] User authentication working
- [ ] Document processing pipeline functional
- [ ] API key management operational
- [ ] Monitoring dashboards showing normal metrics
- [ ] Error budget impact assessed
- [ ] Postmortem scheduled (if outage > 30 minutes or P0)
- [ ] Action items created and assigned
- [ ] Runbooks updated with incident-specific procedures

---

## 11. Testing — Runbook Drills & Validation

### Runbook Drill Procedures

Each runbook procedure has a corresponding drill test that validates the documented steps produce the expected outcome. Drills are automated via CI/CD and run on a rotating schedule.

| Drill | Frequency | Procedure Validated | Pass Criteria |
| --- | --- | --- | --- |
| **Service Restart Drill** | Weekly | Section 6 — Service Restart | All services return health check 200 within 60s |
| **Redis Failover Drill** | Monthly | Section 6 — Redis Flush/Recovery | Rate limiting degrades to in-memory; cache rebuilds correctly |
| **Database PITR Drill** | Quarterly | Section 6 — Database Recovery | Staging DB restored to specified timestamp; data consistent |
| **Pipeline Recovery Drill** | Monthly | Section 6 — Pipeline Recovery | Stuck PROCESSING jobs marked FAILED on restart |
| **LLM Failover Drill** | Monthly | Section 8 — LLM Provider Fallback | Circuit breaker opens; all 4 tiers fall back correctly |
| **ChromaDB Rebuild Drill** | Quarterly | Section 7 — ChromaDB Restore | `kb.json` ingestion completes; RAG queries return results |
| **Full DR Walkthrough** | Semi-annual | All recovery procedures | RTO < 4 h, RPO < 1 h for critical services |
| **Ransomware Simulation** | Annual | Section 9 — Security Incidents | Full isolation + restore from immutable backup < 90 min |

### Chaos Engineering Tests

Chaos tests validate runbook steps by injecting failures into a staging environment:

```python
# test_chaos_redis_outage.py
async def test_redis_outage_triggers_in_memory_fallback(client):
    with patch("app.cache.redis_cache.RedisCache._ensure_client") as mock:
        mock.side_effect = ConnectionError("Redis unreachable")
        response = await client.get("/ready")
        assert response.status_code == 200  # System still responds
        # Rate limiting falls back to in-memory
        assert "Redis" not in response.json().get("checks", {})

# test_chaos_grobid_outage.py
async def test_grobid_outage_triggers_docling_fallback(client):
    with patch("app.pipeline.services.grobid_client.GrobidClient.parse_pdf") as mock:
        mock.side_effect = TimeoutError("GROBID timeout")
        result = await orchestrator.run_pipeline(...)
        assert result["parsing_source"] == "docling"
```

### API Reference — Health Check Endpoints for Automated Monitoring

| Endpoint | Purpose | Recommended Sleep | Alert on |
| --- | --- | --- | --- |
| `GET /health` | Liveness — always returns 200 | 30s | Non-200 response |
| `GET /ready` | Readiness — returns 503 if degraded | 15s | 3 consecutive 503s |
| `GET /api/v1/health/live` | Render/K8s liveness probe | 30s | Non-200 |
| `GET /api/v1/health/ready` | Strict readiness with dependency details | 15s | 503 for > 2 min |
| `GET /metrics` | Prometheus scrape | 15s | Scrape failure |

Automated monitoring script pattern:

```bash
#!/bin/bash
# health_monitor.sh — run as cron every 30s
ENDPOINTS=(
  "https://api.scholarform.ai/health"
  "https://api.scholarform.ai/ready"
  "https://api.scholarform.ai/api/v1/health/live"
)

for ep in "${ENDPOINTS[@]}"; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "$ep" || echo "000")
  if [ "$status" != "200" ] && [ "$ep" != "/ready" ]; then
    echo "ALERT: $ep returned $status at $(date)"
    # Send to PagerDuty / Slack
  fi
done
```

*This runbook is reviewed quarterly. Last updated: July 2026.*
*For questions or updates, contact the DevOps team.*
