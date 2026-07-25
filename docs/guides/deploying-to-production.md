<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Guide — Deploying to Production
description: Complete deployment guide for ScholarForm AI to Render, Vercel, and Supabase
sidebar_position: 3
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: monthly
last_updated: July 2026
---

# Guide: Deploying to Production

This guide walks through deploying ScholarForm AI to production across all required services.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│   Browser   │────▶│  Vercel      │────▶│  Render    │
│  (User)     │     │  (Frontend)  │     │  (Backend) │
└─────────────┘     └──────────────┘     └─────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────┐
                    │                          │          │
                    ▼                          ▼          ▼
             ┌──────────┐            ┌───────────┐ ┌────────┐
             │ Supabase │            │   Redis   │ │ Sentry │
             │ (DB+Auth)│            │ (Upstash) │ │ (Errors)│
             └──────────┘            └───────────┘ └────────┘
```

## Prerequisites

| Service | Account Required | Tier | Est. Cost |
|---------|-----------------|------|-----------|
| [Render](https://render.com) | ✅ Sign up | Professional ($20/mo) | $20/mo |
| [Supabase](https://supabase.com) | ✅ Sign up | Free tier (50K rows) | $0/mo |
| [Upstash Redis](https://upstash.com) | ✅ Sign up | Free tier (256MB) | $0/mo |
| [Vercel](https://vercel.com) | ✅ Sign up | Hobby (free) | $0/mo |
| Custom domain | Optional | DNS provider | $10–20/yr |

### Local Tools

```bash
# Verify installations
git --version        # 2.40+
node --version       # 20.x+
python --version     # 3.12.x
docker --version     # 24+ (optional, for GROBID)
```

## Step 1: Fork/Clone and Configure Environment

```bash
git clone https://github.com/your-org/scholarform.git
cd scholarform
```

### Backend Environment

Copy the template and fill in your production values:

```bash
cp backend/.env.example backend/.env.production
# Edit backend/.env.production with production values
```

**Critical: Generate a secure SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Output: 4f8a3b2c1d... (copy this)
```

### Frontend Environment

```bash
cp frontend/.env.example frontend/.env.production
```

## Step 2: Set Up Supabase

### Create Project

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Choose a region close to your users (e.g., `us-east-1`)
3. Set a strong database password
4. Wait for project initialization (~2 min)

### Get Credentials

From your Supabase project dashboard → **Settings** → **API**:

| Variable | Where to Find |
|----------|---------------|
| `SUPABASE_URL` | Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Settings → API → anon/public key |
| `SUPABASE_SERVICE_KEY` | Settings → API → service_role key |

### Run Schema Migrations

From your local machine with database access configured:

```bash
cd backend
# Point to production DB
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key"

# Run migrations
alembic upgrade head
```

### Configure Authentication

1. **Supabase Dashboard** → **Authentication** → **Settings**
2. Enable **Email + Password** sign-in
3. (Optional) Configure OAuth providers (Google, GitHub)
4. Set `SITE_URL` to your frontend URL (e.g., `https://scholarform.vercel.app`)

### Configure Storage

1. **Supabase Dashboard** → **Storage**
2. Create a bucket named `documents`
3. Set public access policy:

```sql
-- Allow authenticated users to read their own documents
CREATE POLICY "Users can read own documents"
ON storage.objects FOR SELECT
USING (auth.uid()::text = (storage.foldername(name))[1]);

-- Allow authenticated users to upload documents
CREATE POLICY "Users can upload documents"
ON storage.objects FOR INSERT
WITH CHECK (auth.uid()::text = (storage.foldername(name))[1]);
```

## Step 3: Configure Redis (Upstash)

### Create Redis Database

1. Go to [upstash.com](https://upstash.com) → **Create Database**
2. Select the same region as your Render backend
3. Enable **TLS** (required for production)
4. Copy the `UPSTASH_REDIS_URL` (wrapped in `rediss://`)

### Verify Connection

```bash
redis-cli -u "rediss://default:password@us1-steady-whale-12345.upstash.io:6379" ping
# Expected: PONG
```

## Step 4: Deploy Backend to Render

### Create Web Service

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `scholarform-api` |
| **Region** | Same as Supabase/Upstash |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port 10000` |
| **Plan** | Starter ($7/mo) or Free |

### Set Environment Variables

In Render dashboard → **Environment**:

```bash
# Required
ENVIRONMENT=production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
SECRET_KEY=your-32-byte-secret-hex
ENCRYPTION_KEY=your-fernet-key-base64

# Redis
REDIS_URL=rediss://default:password@us1-redis.upstash.io:6379

# LLM Providers (at least one)
NVIDIA_API_KEY=nvapi-your-key
GROQ_API_KEY=gsk_your-key

# Optional
LOG_LEVEL=INFO
LOW_MEMORY_MODE=true
PRELOAD_AI_MODELS=false
DEFAULT_FAST_MODE=true
MAX_UPLOAD_SIZE_MB=50
CORS_ORIGINS=https://scholarform.vercel.app
FORCE_HTTPS=true
```

### Create Celery Worker

1. **Render Dashboard** → **New** → **Background Worker**
2. Connect same repository
3. Configure:

| Setting | Value |
|---------|-------|
| **Name** | `scholarform-worker` |
| **Start Command** | `celery -A app.tasks.celery_tasks worker -Q interactive,batch --concurrency=2` |
| **Plan** | Starter ($7/mo) |

4. Copy same environment variables from the web service

### Health Check Verification

After deployment completes, verify the health endpoint:

```bash
curl https://scholarform-api.onrender.com/api/v1/health/live
# Expected: {"status":"ok"}

curl https://scholarform-api.onrender.com/api/v1/health/ready
# Expected: {"status":"ok","dependencies":{"db":"ok","redis":"ok"}}
```

## Step 5: Deploy Frontend to Vercel

### Connect Repository

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**
2. Import your GitHub repository
3. Set **Root Directory** to `frontend/`

### Configure Environment Variables

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://your-project.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `your-anon-key` |
| `NEXT_PUBLIC_API_BASE_URL` | `https://scholarform-api.onrender.com` |

### Build & Deploy Settings

| Setting | Value |
|---------|-------|
| **Framework** | Next.js |
| **Build Command** | `npm run build` |
| **Output Directory** | `.next` (auto-detected) |
| **Node Version** | 20.x |

### Verify Deployment

```bash
curl https://scholarform.vercel.app/api/health
# Expected: HTTP 200

# Visit in browser
open https://scholarform.vercel.app
```

## Step 6: Configure Custom Domain and SSL

### Vercel Domain

1. **Vercel Dashboard** → **Project** → **Domains**
2. Add your domain: `app.scholarform.ai`
3. Follow Vercel's DNS configuration instructions
4. Vercel automatically provisions SSL via Let's Encrypt

### Render Domain

1. **Render Dashboard** → **Web Service** → **Settings** → **Custom Domain**
2. Add `api.scholarform.ai`
3. Add CNAME record in your DNS provider:

```
api.scholarform.ai  CNAME  scholarform-api.onrender.com
```

### Update Environment Variables

After configuring domains, update:

```bash
# Render
CORS_ORIGINS=https://app.scholarform.ai
SITE_URL=https://app.scholarform.ai

# Vercel
NEXT_PUBLIC_API_BASE_URL=https://api.scholarform.ai
```

## Step 7: Set Up Monitoring

### Error Tracking (Sentry Removed)

Sentry error tracking has been removed. Errors are monitored through Prometheus metrics and structured logging.

To verify error tracking:

```bash
# Trigger test error
curl -X POST https://api.scholarform.ai/api/v1/debug/error-test \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Check metrics dashboard for the error
```

### Uptime Monitoring

Set up a free uptime check (e.g., [Better Uptime](https://betteruptime.com) or [Pingdom](https://pingdom.com)):

| Check | URL | Interval |
|-------|-----|----------|
| API health | `https://api.scholarform.ai/health` | 1 min |
| Frontend | `https://app.scholarform.ai` | 5 min |

### Structured Logging

Render captures stdout logs by default. Configure queryable JSON logging:

```bash
# In Render env vars
LOG_FORMAT=json
LOG_LEVEL=INFO
```

### Grafana & Prometheus (Optional)

For advanced monitoring, deploy Prometheus + Grafana:

```bash
# docker-compose for monitoring stack (production)
docker-compose -f docker-compose.monitoring.yml up -d
```

See the [Monitoring Setup Guide](setting-up-monitoring.md) for complete setup instructions.

## Step 8: Production Checklist Verification

Run through the [Production Readiness Checklist](../PRODUCTION_READINESS_CHECKLIST.md) before going live.

### Critical Items

- [ ] All environment variables set in Render (not tracked in git)
- [ ] `ENVIRONMENT=production` — disables debug endpoints and Swagger
- [ ] `SECRET_KEY` is a cryptographically random 64-char hex string
- [ ] `ENCRYPTION_KEY` is set (not auto-generated)
- [ ] `FORCE_HTTPS=true` — redirects all HTTP to HTTPS
- [ ] CORS origins limited to your frontend domain
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Health endpoint returns `200 OK`
- [ ] Ready endpoint shows all dependencies green
- [ ] Sentry error tracking verified
- [ ] SSL certificates active (auto by Vercel/Render)

### Performance Items

- [ ] Celery worker running with `--concurrency=2` or higher
- [ ] `LOW_MEMORY_MODE=true` (recommended for Render free/starter)
- [ ] `DEFAULT_FAST_MODE=true` (skips optional heavy AI stages)
- [ ] Redis cache configured and accessible
- [ ] Database indexes created (see alembic migrations)

### Security Items

- [ ] CSP headers configured (`security_headers.py`)
- [ ] Rate limiting active (100 req/min default)
- [ ] File upload size limited (50MB default)
- [ ] Virus scanning active (if ClamAV configured)
- [ ] No `.env` files in git history
- [ ] Regular secret rotation scheduled

## Rollback Procedures

### Frontend Rollback (Vercel)

```bash
# Via Vercel dashboard
# 1. Go to Deployments
# 2. Find last known-good deployment
# 3. Click "..." → "Promote to Production"

# Via CLI
vercel rollback --yes
```

### Backend Rollback (Render)

```bash
# Via Render dashboard
# 1. Go to your web service
# 2. Click "Manual Deploy" → "Deploy previous deploy"
# 3. Select the last known-good deploy

# Note: Render also auto-deploys if you revert the git commit
git revert HEAD
git push origin main
```

### Database Rollback

```bash
cd backend
alembic downgrade -1  # Roll back one migration
alembic history       # View migration history
```

### Full Rollback Runbook

See the [Rollback Runbook](../runbooks/rollback.md) for detailed procedures.

## Environment Variable Reference

### Backend (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment name | `production` |
| `SUPABASE_URL` | Supabase project URL | `https://abc123.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGciOi...` |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | `eyJhbGciOi...` |
| `SECRET_KEY` | JWT signing secret (64 hex chars) | `4f8a3b2c...` |
| `ENCRYPTION_KEY` | Fernet key (base64, 32 bytes) | `dGhpcyBpcyBhIHRlc3Qga2V5...` |
| `REDIS_URL` | Redis connection string | `rediss://user:pass@host:6379` |

### Backend (LLM Providers — at least one required)

| Variable | Description | Example |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | NVIDIA NIM API key | `nvapi-abc123...` |
| `GROQ_API_KEY` | Groq API key | `gsk_abc123...` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-abc123...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-abc123...` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |

### Backend (Optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_FORMAT` | Log output format | `text` |
| `LOW_MEMORY_MODE` | Optimize for low memory | `true` |
| `PRELOAD_AI_MODELS` | Preload AI models on startup | `false` |
| `DEFAULT_FAST_MODE` | Skip optional AI stages | `true` |
| `MAX_UPLOAD_SIZE_MB` | Max upload file size | `50` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |
| `FORCE_HTTPS` | Redirect HTTP to HTTPS | `false` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `100` |
| `GROBID_URL` | GROBID service URL | `http://localhost:8070` |
| `GROBID_ENABLED` | Enable GROBID PDF parsing | `false` |
| `CHROMA_PERSIST_DIR` | ChromaDB persistence path | `./chroma_db` |
| `STRIPE_SECRET_KEY` | Stripe secret key | — |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | — |

### Frontend (Required)

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | `https://abc123.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | `eyJhbGciOi...` |
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL | `https://api.scholarform.ai` |

### Frontend (Optional)

| Variable | Description | Default |
|----------|-------------|---------|

## Related Resources

| Resource | Description |
|----------|-------------|
| [Deployment Guide (Legacy)](../Deployment.md) | Original deployment documentation |
| [Disaster Recovery](../DISASTER_RECOVERY.md) | Backup, restore, and DR procedures |
| [Monitoring Setup](setting-up-monitoring.md) | Complete monitoring configuration guide |
| [Secret Rotation](../SECRET_ROTATION.md) | Credential rotation procedures |
| [Operations Runbook](../OPERATIONS_RUNBOOK.md) | Day-to-day operations |
| [Rollback Runbook](../runbooks/rollback.md) | Detailed rollback procedures |
| [Production Readiness Checklist](../PRODUCTION_READINESS_CHECKLIST.md) | Pre-launch verification |
