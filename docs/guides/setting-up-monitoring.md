<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Guide — Setting Up Monitoring
description: Complete monitoring setup guide with Prometheus, Grafana, Sentry, structured logging, and alerting
sidebar_position: 4
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: monthly
last_updated: July 2026
---

# Guide: Setting Up Monitoring

This guide covers the complete monitoring and observability stack for ScholarForm AI in production.

## Monitoring Stack Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                          │
├─────────────────┬───────────────────┬───────────────────────┤
│   Prometheus    │     Grafana       │       Sentry          │
│  (Metrics)      │   (Dashboards)    │   (Error Tracking)    │
├─────────────────┼───────────────────┼───────────────────────┤
│   /metrics      │  JSON dashboards  │  Backend + Frontend   │
│   endpoint      │  + alert rules    │  exception capture    │
├─────────────────┼───────────────────┼───────────────────────┤
│   PostHog       │  Structured Logs  │   Uptime Checks       │
│  (Analytics)    │  (JSON stdout)    │   (Health endpoint)   │
└─────────────────┴───────────────────┴───────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Data Retention | Cost |
|-----------|---------|---------------|------|
| **Prometheus** | Time-series metrics storage | 15 days (default) | Free (self-hosted) |
| **Grafana** | Dashboard visualization + alerting | — | Free tier (cloud) |
| **Sentry** | Error tracking and performance | 30 days (free) | Free (5K events/mo) |
| **PostHog** | Product analytics, session recording | 7 days (free) | Free (1M events/mo) |
| **Better Uptime** | External uptime monitoring | — | Free (1 check) |
| **Render Logs** | Application log aggregation | 7 days | Included |

## Step 1: Set Up Prometheus Metrics Endpoint

ScholarForm exports Prometheus metrics at `/metrics` via the `prometheus_metrics.py` middleware.

### Verify Metrics Endpoint

```bash
curl http://localhost:8000/metrics \
  -H "Authorization: Bearer ADMIN_JWT"
```

**Expected output (sample):**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/health",status="200"} 1523
http_requests_total{method="POST",endpoint="/api/v1/documents/upload",status="200"} 847

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/api/v1/health",le="0.005"} 1489
http_request_duration_seconds_bucket{endpoint="/api/v1/health",le="0.01"} 1520
http_request_duration_seconds_bucket{endpoint="/api/v1/health",le="+Inf"} 1523

# HELP pipeline_stage_duration_seconds Pipeline stage duration
# TYPE pipeline_stage_duration_seconds histogram
pipeline_stage_duration_seconds_bucket{stage="parsing",le="1.0"} 712
pipeline_stage_duration_seconds_bucket{stage="formatting",le="5.0"} 680

# HELP llm_tokens_total LLM tokens consumed
# TYPE llm_tokens_total counter
llm_tokens_total{provider="nvidia",model="llama-3.3-70b"} 2847321
llm_tokens_total{provider="groq",model="llama-3.3-70b"} 521843

# HELP llm_tier_usage_total LLM tier fallback usage
# TYPE llm_tier_usage_total counter
llm_tier_usage_total{tier="primary"} 732
llm_tier_usage_total{tier="fallback"} 89
llm_tier_usage_total{tier="rule_based"} 12

# HELP circuit_breaker_state Circuit breaker state (0=closed, 1=open, 2=half-open)
# TYPE circuit_breaker_state gauge
circuit_breaker_state{circuit="nvidia_nim"} 0
```

### Available Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | endpoint | Request latency distribution |
| `pipeline_stage_duration_seconds` | Histogram | stage | Per-pipeline-stage duration |
| `llm_tokens_total` | Counter | provider, model | LLM tokens consumed |
| `llm_tier_usage_total` | Counter | tier | Primary vs fallback LLM usage |
| `circuit_breaker_state` | Gauge | circuit | Circuit breaker state (0/1/2) |
| `active_processing_jobs` | Gauge | — | Currently processing documents |
| `audit_log_available` | Gauge | — | Audit log service health (0/1) |

### Configure Prometheus Scrape

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'scholarform'
    scrape_interval: 15s
    metrics_path: '/metrics'
    scheme: https
    authorization:
      type: Bearer
      credentials: 'YOUR_ADMIN_JWT'
    static_configs:
      - targets: ['api.scholarform.ai']
        labels:
          service: 'backend'
```

### Self-Hosted Prometheus with Docker

```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:v2.53.0
    volumes:
      - ./ops/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./ops/prometheus/alerts/:/etc/prometheus/alerts/
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=15d'

volumes:
  prometheus_data:
```

```bash
docker compose -f docker-compose.monitoring.yml up -d prometheus
```

## Step 2: Configure Grafana Dashboards

### Deploy Grafana

```yaml
# docker-compose.monitoring.yml (add to above)
  grafana:
    image: grafana/grafana:11.1.0
    volumes:
      - ./ops/grafana/provisioning/:/etc/grafana/provisioning/
      - ./ops/grafana/dashboards/:/var/lib/grafana/dashboards/
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure-password-here
      - GF_INSTALL_PLUGINS=grafana-piechart-panel

volumes:
  grafana_data:
```

```bash
docker compose -f docker-compose.monitoring.yml up -d grafana
```

### Provision Datasource

Create `ops/grafana/provisioning/datasources/prometheus.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### Import Dashboards

Create `ops/grafana/provisioning/dashboards/scholarform.yml`:

```yaml
apiVersion: 1
providers:
  - name: ScholarForm
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 60
    options:
      path: /var/lib/grafana/dashboards
```

### Dashboard Panels

The **ScholarForm Overview** dashboard includes:

```
┌─────────────────────────────────────────────────────┐
│  REQUEST RATE (req/s)    │  ERROR RATE (%)          │
│  ████████████████░ 12.4  │  ██░░░░░░░░░░░░░░ 1.2%  │
├──────────────────────────┼──────────────────────────┤
│  P50 LATENCY (ms)        │  P95 LATENCY (ms)        │
│  ████████░░░░░░░░░ 45ms  │  ████████████████░ 320ms │
├──────────────────────────┼──────────────────────────┤
│  P99 LATENCY (ms)        │  ACTIVE JOBS             │
│  ████████████████░ 890ms │  ████░░░░░░░░░░░░░ 3     │
├──────────────────────────┼──────────────────────────┤
│  LLM TIER USAGE          │  CIRCUIT BREAKER         │
│  ┌─────────────┐  Primary│  NVIDIA:  ● CLOSED       │
│  │████████████░░│  732   │  Groq:    ● CLOSED       │
│  │███░░░░░░░░░░░│   89   │  Ollama:  ● OPEN         │
│  │░░░░░░░░░░░░░░│   12   │                          │
│  └─────────────┘  Rule   │                          │
└─────────────────────────────────────────────────────┘
```

Panel descriptions:

| Panel | Metric | Query | Threshold |
|-------|--------|-------|-----------|
| **Request Rate** | `sum(rate(http_requests_total[5m]))` | Per-endpoint breakdown | — |
| **Error Rate** | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100` | > 1% warning, > 5% critical |
| **P50 Latency** | `histogram_quantile(0.5, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | < 100ms target |
| **P95 Latency** | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | < 500ms target |
| **P99 Latency** | `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | < 2s target |
| **Active Jobs** | `active_processing_jobs` | < 50 normal |
| **LLM Tier Usage** | `sum(llm_tier_usage_total) by (tier)` | Fallback > 10% = investigate |
| **Circuit Breaker** | `circuit_breaker_state` | 1 = OPEN (alert) |

## Step 3: Set Up Sentry for Error Tracking

### Backend (Python/FastAPI)

Install and configure:

```bash
pip install sentry-sdk
```

In `backend/app/main.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.25,  # Sample 25% of requests
        profiles_sample_rate=0.10,  # Sample 10% for profiling
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=False,
    )
```

Verify Sentry is working:

```bash
# Create test error (admin only)
curl -X POST https://api.scholarform.ai/api/v1/debug/sentry-test \
  -H "Authorization: Bearer ADMIN_JWT"

# Check https://sentry.io for the captured error
```

### Backend Environment Variables

```bash
SENTRY_DSN=https://public_key@o123.ingest.sentry.io/project_id
```

### Frontend (Next.js)

Install:

```bash
cd frontend
npm install @sentry/nextjs
```

Configure in `frontend/sentry.client.config.ts`:

```typescript
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_VERCEL_ENV || "development",
  tracesSampleRate: 0.25,
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,
  integrations: [Sentry.replayIntegration()],
});
```

### Alert Rules in Sentry

Configure these alert rules in Sentry:

| Alert | Condition | Action |
|-------|-----------|--------|
| **New Error** | First occurrence of an issue | Email to team + Slack notification |
| **Error Spike** | > 10 errors in 5 minutes | PagerDuty call + Slack |
| **High Frequency** | Same error affects > 50 users in 1 hour | Email + Slack |

## Step 4: Configure Structured Logging

### JSON Log Format

Set the following in your Render environment:

```bash
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Produces log entries like:

```json
{
  "timestamp": "2026-07-17T10:00:00.123Z",
  "level": "INFO",
  "logger": "app.routers.v1.documents",
  "message": "Document upload completed",
  "request_id": "req_abc123",
  "user_id": "user_456",
  "document_id": "doc_789",
  "duration_ms": 2347,
  "template": "ieee",
  "file_size_bytes": 245760
}
```

### Security Event Logging

Security events are logged at `WARNING` level with structured context:

```json
{
  "timestamp": "2026-07-17T10:05:00.123Z",
  "level": "WARNING",
  "logger": "app.middleware.security",
  "message": "Rate limit threshold crossed",
  "request_id": "req_def456",
  "client_ip": "203.0.113.42",
  "user_id": "user_789",
  "limit": 100,
  "current_count": 101,
  "endpoint": "/api/v1/documents/upload"
}
```

Events logged as security events:

| Event | Level | Fields |
|-------|-------|--------|
| Authentication failure | WARNING | email (hashed), client_ip, reason |
| Rate limit exceeded | WARNING | user_id, endpoint, current_count, limit |
| Abuse detected | WARNING | client_ip, pattern, score |
| Invalid JWT | WARNING | token_jti (partial), reason |
| CSRF validation failure | WARNING | client_ip, user_id |
| File upload validation failure | WARNING | user_id, filename, reason |

### Log Querying on Render

Render provides a built-in log viewer:

1. **Render Dashboard** → **Your Service** → **Logs**
2. Filter by log level: `level=ERROR`
3. Filter by request: `request_id=req_abc123`
4. Export logs for retention (up to 7 days)

For longer retention, configure a log drain:

```bash
# Render → Your Service → Settings → Log Drains
# Add HTTP endpoint (e.g., Logz.io, Datadog, Axiom)
```

## Step 5: Set Up Uptime Monitoring

### Health Check Endpoints

ScholarForm exposes three health endpoints:

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /health` | Basic liveness probe | `{"status": "ok"}` |
| `GET /ready` | Readiness with dependency check | `{"status": "ok", "dependencies": {"db": "ok", "redis": "ok"}}` |
| `GET /api/v1/health` | API v1 health with version info | `{"status": "ok", "version": "1.0.0"}` |

### Configure Uptime Checks (Better Uptime)

1. Sign up at [betteruptime.com](https://betteruptime.com)
2. Create a monitor:

| Setting | Value |
|---------|-------|
| **URL** | `https://api.scholarform.ai/health` |
| **Check Interval** | 1 minute |
| **Timeout** | 10 seconds |
| **Expected status** | 200 |
| **Regions** | US East, US West, EU West |

3. Configure notification:

| Channel | Trigger |
|---------|---------|
| Email | On first failure |
| Slack | On failure + recovery |
| SMS | If down > 5 minutes |

### Self-Hosted Uptime Monitoring (Uptime Kuma)

```bash
docker run -d --name uptime-kuma \
  -p 3002:3001 \
  -v uptime-kuma-data:/app/data \
  louislam/uptime-kuma:1
```

## Step 6: Configure Alerting

### Prometheus Alert Rules

Create `ops/prometheus/alerts/scholarform-alerts.yml`:

```yaml
groups:
  - name: scholarform
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          (sum(rate(http_requests_total{status=~"5.."}[5m]))
           /
           sum(rate(http_requests_total[5m]))) * 100 > 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 1% (current: {{ $value }}%)"
          runbook: "docs/runbooks/incident-response.md"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 1s (current: {{ $value }}s)"

      - alert: QueueBackup
        expr: active_processing_jobs > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Processing queue backup ({{ $value }} jobs pending)"

      - alert: LLMFailures
        expr: |
          (sum(rate(llm_tier_usage_total{tier="fallback"}[5m]))
           /
           sum(rate(llm_tier_usage_total[5m]))) * 100 > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM fallback rate above 50% — primary provider may be down"

      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker OPEN for {{ $labels.circuit }}"

      - alert: AuditLogDown
        expr: audit_log_available == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Audit log service unavailable"

      - alert: ServiceDown
        expr: probe_success == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service unreachable — health check failing"
```

### Alert Notification Channels

| Channel | Setup | Cost |
|---------|-------|------|
| **Slack** | Grafana → Alerting → Contact Points → Slack webhook URL | Free |
| **Email** | Grafana → Alerting → Contact Points → SMTP config | Free |
| **PagerDuty** | Grafana → Alerting → Contact Points → PagerDuty integration key | Paid |

### Grafana Notification Configuration

```bash
# Grafana env vars for Slack alerting
GF_EXTERNAL_IMAGE_STORAGE_PROVIDER=webdav
GF_ALERTING_ENABLED=true
GF_UNIFIED_ALERTING_ENABLED=true
```

## Step 7: Set Up Real User Monitoring (RUM)

### PostHog for Product Analytics

1. Sign up at [posthog.com](https://posthog.com)
2. Create a project and get your API key

Backend setup (`backend/app/services/analytics_service.py`):

```python
from posthog import Posthog
from app.config import settings

posthog = Posthog(
    project_api_key=settings.POSTHOG_API_KEY,
    host=settings.POSTHOG_HOST or "https://app.posthog.com"
)

def track_event(user_id: str, event: str, properties: dict = None):
    """Track a user event in PostHog."""
    if settings.POSTHOG_API_KEY:
        posthog.capture(user_id, event, properties)
```

Events to track:

| Event | Properties | Purpose |
|-------|------------|---------|
| `upload_started` | template, file_size, file_type | Measure upload funnel |
| `upload_completed` | duration_ms, success | Measure processing success |
| `format_downloaded` | format (docx/pdf) | Measure export preferences |
| `agent_session_started` | template, tone | Measure AI feature adoption |
| `synthesis_started` | source_count, strategy | Measure multi-doc usage |
| `synthesis_completed` | quality_score, duration_ms | Measure synthesis quality |
| `template_created` | template_name | Measure custom template usage |

Frontend setup:

```bash
cd frontend
npm install posthog-js
```

```typescript
// frontend/src/lib/posthog.ts
import posthog from "posthog-js";

if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com",
    capture_pageview: true,
    capture_pageleave: true,
  });
}

export default posthog;
```

### Web Vitals Tracking (LCP, FID, CLS)

Next.js automatically tracks Core Web Vitals. Configure reporting in `frontend/src/app/reportWebVitals.ts`:

```typescript
export function reportWebVitals(metric: any) {
  if (process.env.NEXT_PUBLIC_POSTHOG_KEY) {
    const posthog = require("../lib/posthog").default;
    posthog.capture("web_vitals", metric);
  }
}
```

Target thresholds:

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| **LCP** (Loading) | ≤ 2.5s | 2.5s – 4.0s | > 4.0s |
| **FID** (Interactivity) | ≤ 100ms | 100ms – 300ms | > 300ms |
| **CLS** (Visual Stability) | ≤ 0.1 | 0.1 – 0.25 | > 0.25 |

## Dashboard Reference

### Key Queries for Grafana Panels

```promql
# Request rate by endpoint
sum(rate(http_requests_total[5m])) by (endpoint)

# Error rate percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# P95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# LLM fallback ratio
sum(llm_tier_usage_total{tier="fallback"}) / sum(llm_tier_usage_total) * 100

# Active processing jobs over time
avg_over_time(active_processing_jobs[15m])
```

### Alert Thresholds Summary

| Alert | Severity | Threshold | Duration |
|-------|----------|-----------|----------|
| High Error Rate | CRITICAL | > 1% 5xx | 5 min |
| High Latency (P95) | WARNING | > 1s | 5 min |
| Queue Backup | WARNING | > 50 jobs | 10 min |
| LLM Failures | WARNING | > 50% fallback | 5 min |
| Circuit Breaker Open | CRITICAL | any | 1 min |
| Audit Log Down | WARNING | 0 | 1 min |
| Service Down | CRITICAL | probe fails | 1 min |

## Troubleshooting Monitoring

| Issue | Cause | Solution |
|-------|-------|----------|
| `/metrics` returns 401 | Missing or expired admin JWT | Generate a new admin token or disable auth on `/metrics` in dev |
| Prometheus can't scrape | Network access or TLS issues | Ensure `--web.listen-address=0.0.0.0:9090` or use a proxy |
| Grafana shows "No data" | Datasource not connected or wrong URL | Verify Prometheus datasource in Grafana → Configuration → Data Sources |
| Sentry not capturing errors | DSN misconfigured or `send_default_pii=false` blocking | Test with `/api/v1/debug/sentry-test`; check sentry_sdk.init() |
| Logs not appearing in Render | Log drain misconfigured | Check Render → Service → Logs → Drain URL |

## Related Resources

| Resource | Description |
|----------|-------------|
| [Deploying to Production Guide](deploying-to-production.md) | Full production deployment |
| [Operations Runbook](../OPERATIONS_RUNBOOK.md) | Day-to-day operations |
| [Incident Response Runbook](../runbooks/incident-response.md) | P0/P1 incident procedures |
| [SLO Definitions](../SLO_DEFINITIONS.md) | Service level objectives and SLIs |
| [Prometheus Metrics Source](../backend/app/middleware/prometheus_metrics.py) | Source code for metrics |
