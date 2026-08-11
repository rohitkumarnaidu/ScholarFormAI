<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI v1.0 — Operations Handbook
description: Enterprise operations reference covering monitoring, logging, alerting, incident response, backup, deployment, on-call, maintenance, and runbooks
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI v1.0 — Operations Handbook

> **Document Purpose:** This handbook is the single source of truth for operating ScholarForm AI in production. It covers every phase of the operational lifecycle — from day-to-day monitoring and on-call duties, to incident response, disaster recovery, and scheduled maintenance.

**Service:** ScholarForm AI (Document Formatting Platform)  
**Version:** 1.0  
**Stack:** FastAPI (Python 3.12), React, PostgreSQL (Supabase), Redis, ChromaDB, Celery, Render, Vercel  
**Deployment:** Render (backend), Vercel (frontend)  
**Infrastructure as Code:** GitHub — branch protection enforced in `main`

---

## Table of Contents

1. [Monitoring](#1-monitoring)
2. [Logging](#2-logging)
3. [Alerting](#3-alerting)
4. [Incident Response](#4-incident-response)
5. [Backup & Recovery](#5-backup--recovery)
6. [Deployment](#6-deployment)
7. [On-Call](#7-on-call)
8. [Maintenance](#8-maintenance)
9. [Runbooks Index](#9-runbooks-index)

---

## 1. Monitoring

### 1.1 Prometheus Metrics

ScholarForm AI exposes a `/api/v1/metrics` endpoint on the backend service, scraped by a Prometheus instance hosted on Render's internal monitoring infrastructure.

**Core Application Metrics:**

| Metric | Type | Labels | Description |
| -------- | ------ | -------- | ------------- |
| `http_requests_total` | Counter | `path, method, status` | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | `path, method` | Request latency buckets |
| `celery_queue_depth` | Gauge | `queue` | Current Celery task queue depth |
| `celery_task_duration_seconds` | Histogram | `task_name` | Task execution time |
| `llm_request_duration_seconds` | Histogram | `provider, model` | LLM API call latency |
| `llm_request_total` | Counter | `provider, model, status` | LLM API call count |
| `clamav_scan_duration_seconds` | Histogram | — | File scan duration |
| `sse_connections_active` | Gauge | — | Active SSE connections |
| `chroma_collection_count` | Gauge | `collection` | ChromaDB vector collections |
| `redis_connected_clients` | Gauge | — | Redis client connections |
| `circuit_breaker_state` | Gauge | `name` | Circuit breaker state (0=closed, 1=open, 2=half-open) |

**Infrastructure Metrics (Render):**

| Metric | Source | Description |
| -------- | -------- | ------------- |
| `cpu_usage_percent` | Render dashboard | Container CPU utilization |
| `memory_usage_bytes` | Render dashboard | Container memory utilization |
| `disk_usage_bytes` | Render dashboard | Container disk usage |
| `instance_count` | Render dashboard | Active instance count |
| `deploy_status` | Render API | Last deploy status (success/failure) |

### 1.2 Grafana Dashboards

Three dashboards are provisioned in the Grafana instance at `https://grafana.scholarform.ai`:

**Dashboard 1: Application Performance**

- Panels: HTTP request rate (RPS), p50/p95/p99 latency, error rate %, top slowest endpoints, Celery queue depth, task duration heatmap, LLM provider latency comparison, circuit breaker states
- Refresh: 30s
- Time range default: Last 1 hour

**Dashboard 2: Infrastructure Health**

- Panels: CPU/memory/disk per service, instance count, deploy events timeline, database connection count, Redis memory used, ChromaDB collection sizes, Render status overlay
- Refresh: 60s
- Time range default: Last 24 hours

**Dashboard 3: Business & SLOs**

- Panels: Error budget burn rate, uptime %, documents processed (daily), average format time, active users (SSE connections), format success rate, LLM token usage (daily), per-endpoint SLO compliance
- Refresh: 5m
- Time range default: Last 7 days

### 1.3 Health Check Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /api/v1/health/live` | Liveness probe — service is running | `200 OK` |
| `GET /api/v1/health/ready` | Readiness probe — dependencies available | `200 OK` with status payload |

The readiness endpoint checks: PostgreSQL connectivity, Redis ping, ChromaDB heartbeat, and LLM provider reachability (circuit-breaker aware).

### 1.4 SLIs & SLOs

| SLI | Definition | Target (SLO) | Measurement Window |
| ----- | ----------- | -------------- | ------------------- |
| API Availability | % of requests returning 2xx/4xx (not 5xx) | 99.9% | 30-day rolling |
| API Latency (p95) | p95 of `http_request_duration_seconds` | < 1s | 30-day rolling |
| Format Latency (p95) | p95 end-to-end document format time | < 10s | 30-day rolling |
| Error Rate | % of 5xx responses of total requests | < 1% | 10-minute window |
| Queue Depth | Celery task queue length | < 100 | 10-minute window |
| LLM Availability | % of LLM calls that succeed | 99.5% | 30-day rolling |
| Document Integrity | % of formatted docs without corruption | 99.99% | 30-day rolling |

---

## 2. Logging

### 2.1 OpenTelemetry Tracing

All backend services export OpenTelemetry traces to the OpenTelemetry Collector running as a sidecar. Traces are forwarded to Grafana Tempo for storage and querying.

- **Sampling:** Head-based sampling at 10% for requests under p95; 100% sampling for requests exceeding p95 latency or returning 5xx.
- **Trace context:** Propagated via W3C Trace Context (`traceparent` header).
- **Key spans:** HTTP request handling, Celery task execution, LLM provider calls, database queries, ChromaDB vector search, file I/O.

### 2.2 Log Levels

| Level | Usage | Examples |
| ------- | ------- | ---------- |
| `ERROR` | Service is degraded, action required | DB connection failure, LLM provider timeout, unhandled exceptions |
| `WARN` | Potential issue, no immediate action | Circuit breaker opening, retry attempts, deprecation warnings |
| `INFO` | Normal operational events | Request start/end, deployment events, user signup, document format |
| `DEBUG` | Diagnostic detail, production disabled by default | SQL queries, variable dumps, trace data |

**Note:** `DEBUG` logging is toggled via the `LOG_LEVEL` environment variable and should only be enabled temporarily for root cause analysis.

### 2.3 Log Aggregation

Logs from all services are shipped to the Grafana Loki cluster via Promtail:

- **Backend:** JSON-structured logs written to stdout → captured by Render's log drain → forwarded to Loki.
- **Celery workers:** Same pipeline as backend.
- **Frontend:** Client-side errors are captured via Sentry and also shipped to Loki as structured events.

**Log retention:** 30 days in Loki hot storage; archived to cold storage (S3) for 1 year.

### 2.4 Structured Logging Format

All backend logs follow this JSON schema:

```json
{
  "timestamp": "2026-07-21T14:30:00.123Z",
  "level": "INFO",
  "logger": "scholarform.api",
  "trace_id": "a1b2c3d4e5f6g7h8",
  "span_id": "i9j0k1l2m3n4o5p6",
  "service": "scholarform-backend",
  "message": "Document formatted successfully",
  "resource": {
    "document_id": "doc-abc123",
    "user_id": "usr-456",
    "format_type": "ieee",
    "duration_ms": 2340
  }
}
```

---

## 3. Alerting

### 3.1 Alertmanager Configuration

Prometheus Alertmanager is configured at `https://alertmanager.scholarform.ai` with the following receivers:

- **Slack:** `#incidents` channel for P0/P1 alerts; `#deployments` for deploy events.
- **Email:** <ops@scholarform.ai> for P2 alerts.
- **PagerDuty:** P0/P1 alerts routed to the on-call escalation policy.

### 3.2 Alert Severity Levels

| Severity | Label | Response Time | Channel | Auto-Ack Window |
| ---------- | ------- | --------------- | --------- | ----------------- |
| P0 — Critical | `severity="critical"` | < 5 minutes | PagerDuty + Slack #incidents | 2 minutes |
| P1 — High | `severity="high"` | < 15 minutes | PagerDuty + Slack #incidents | 5 minutes |
| P2 — Medium | `severity="medium"` | < 1 hour | Slack #incidents | 15 minutes |
| P3 — Low | `severity="low"` | < 24 hours | Slack #incidents (digest) | — |

### 3.3 Alert Rules

| Alert Name | Severity | Condition | Duration |
| ----------- | ---------- | ----------- | ---------- |
| `ScholarFormServiceDown` | P0 | `up{job="scholarform"} == 0` | 2m |
| `ScholarFormHighErrorRate` | P1 | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` | 5m |
| `ScholarFormHighLatency` | P1 | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5` | 5m |
| `ScholarFormReadinessUnhealthy` | P1 | `probe_success{job="scholarform-readiness"} == 0` | 5m |
| `CeleryQueueBacklog` | P1 | `celery_queue_depth > 100` | 10m |
| `LLMFailureSpike` | P1 | `rate(llm_request_total{status="error"}[5m]) > 0.1` | 5m |
| `SSEConnectionDrop` | P2 | `sse_connections_active < expected_baseline * 0.5` | 5m |
| `ClamAVSlowScans` | P2 | `histogram_quantile(0.95, rate(clamav_scan_duration_seconds_bucket[5m])) > 5` | 5m |
| `DiskUsageHigh` | P2 | `disk_usage_percent > 85` | 10m |
| `RedisMemoryHigh` | P3 | `redis_memory_used_bytes / redis_max_memory_bytes > 0.8` | 15m |

### 3.4 Alert Routing

Alerts are routed based on severity and alert name:

1. **P0 routes** to PagerDuty immediate with Slack notification. Assignment: primary on-call engineer.
2. **P1 routes** to PagerDuty (non-immediate, 5-min ack window) with Slack notification. Assignment: on-call engineer.
3. **P2 routes** to Slack #incidents only. No automatic PagerDuty escalation.
4. **P3 routes** to Slack #incidents via daily digest. No page.

### 3.5 On-Call Rotation

On-call scheduling is managed through PagerDuty with a weekly rotation.

- **Primary:** Handles P0/P1 alerts, owns incident response.
- **Secondary:** Backup for primary, handles P2 alerts, supports primary during active incidents.
- **Schedule:** Monday 09:00 UTC → Monday 09:00 UTC rotation.

See [On-Call](#7-on-call) section for detailed shift schedule and handoff procedures.

### 3.6 Escalation Policy

| Level | Contact | Escalation After | Notes |
| ------- | --------- | ------------------ | ------- |
| L1 — Primary On-Call | DevOps Engineer | Immediate | First responder |
| L2 — Secondary On-Call | DevOps Engineer | 15 min if P0 unacked | Backup responder |
| L3 — Engineering Lead | Engineering Manager | 30 min if P0 unacked | Coordinates cross-team |
| L4 — VP Engineering | VP Engineering | 60 min if P0 unacked | Business continuity |

---

## 4. Incident Response

### 4.1 Severity Definitions

| Severity | Definition | Examples | Response Time |
| ---------- | ----------- | ---------- | --------------- |
| **P0 — Critical** | Complete service outage or data loss. Core functionality unavailable to all users. | — All API endpoints returning 5xx — Database unreachable — LLM provider fully down — Data corruption detected | < 5 minutes |
| **P1 — High** | Severe degradation of core functionality. Subset of users affected or SLO breach imminent. | — Error rate > 5% — p95 latency > 5s — Document formatting failures > 10% — Queue backlog > 100 tasks | < 15 minutes |
| **P2 — Medium** | Partial degradation. Non-critical feature unavailable. No SLO breach. | — SSE connection instability — ClamAV scanning slow — Individual endpoint latency spike — Non-critical UI defect | < 1 hour |
| **P3 — Low** | Minor issue. No user-facing impact. Cosmetic or operational nuisance. | — Dashboard metric delay — Stale cache — Non-blocking warning log — Deprecation notice | < 24 hours |

### 4.2 Incident Lifecycle

```
Detection → Triage → Containment → Resolution → Follow-up
```

**Detection:** Alerts from Prometheus/Alertmanager, user-reported issues via support channels, or proactive monitoring by on-call engineer.

**Triage:** On-call engineer acknowledges the alert within the response time window (see [Alerting](#3-2-alert-severity-levels)), assesses severity, and begins investigation using the relevant runbook.

**Containment:** Immediate action to limit blast radius — feature flags are toggled off, traffic is rerouted, or the service is rolled back (see [Rollback Runbook](../runbooks/rollback.md)).

**Resolution:** Root cause is identified and fixed. Resolution may include: rolling forward with a fix, reverting a deployment, scaling infrastructure, or switching to a fallback provider.

**Follow-up:** A postmortem is written within 48 hours for P0 and P1 incidents. Postmortems are stored in `docs/postmortems/` and reviewed at the quarterly operations review.

### 4.3 Incident Commander Role

For P0 incidents, the engineer who first responds assumes the **Incident Commander** role. Responsibilities:

- Declare the incident in `#incidents` with severity and summary.
- Coordinate responders and assign tasks.
- Act as the single communication liaison for status updates.
- Track action items during the incident.
- Hand off to a fresh responder if the incident exceeds 4 hours.

### 4.4 Communication Templates

**Incident Declaration (Slack):**

```
🚨 INCIDENT: [short name]
Severity: P[0-3]
Summary: [1-2 sentence description]
Affected: [endpoints / users / features]
Responders: @on-call
Status: Investigating
```

**Incident Update:**

```
Status: [Investigating / Mitigating / Resolved]
Actions taken: [bullet list]
Impact: [current blast radius]
Next steps: [planned actions]
```

**Incident Resolved:**

```
✅ INCIDENT RESOLVED: [short name]
Duration: [X] minutes
Root cause: [one sentence]
Action items: [link to postmortem]
```

### 4.5 Postmortem Process

1. **Create postmortem document** using the template at `docs/POSTMORTEM_TEMPLATE.md`.
2. **Schedule a postmortem meeting** within 5 business days for P0 incidents.
3. **Analyze root cause** using the five whys methodology.
4. **Assign action items** with owners and due dates.
5. **Track action items** in GitHub Issues with label `postmortem`.
6. **Close postmortem** only when all action items are resolved or explicitly deferred.

---

## 5. Backup & Recovery

### 5.1 Database Backup Schedule

| Data Store | Backup Type | Frequency | Retention | Method |
| ----------- | ------------- | ----------- | ----------- | -------- |
| PostgreSQL (Supabase) | Full | Daily | 30 days | Supabase automated backups + `pg_dump` to S3 |
| PostgreSQL (Supabase) | WAL archiving | Continuous | 7 days | Point-in-time recovery enabled |
| ChromaDB | Full (persistent) | Daily | 7 days | Filesystem snapshot + S3 copy |
| Redis | RDB snapshot | Every 6 hours | 3 snapshots | `SAVE` command + upload to S3 |
| Redis | AOF | Continuous | — | Append-only file (AOF) enabled |

### 5.2 ChromaDB Backup

ChromaDB stores vector embeddings persistently on disk at `CHROMA_PERSIST_DIR`. Backup procedure:

```bash
# Manual backup
tar -czf chroma-backup-$(date +%Y%m%d).tar.gz -C $CHROMA_PERSIST_DIR .
aws s3 cp chroma-backup-*.tar.gz s3://scholarform-backups/chromadb/

# Automated (cron): Daily at 02:00 UTC
0 2 * * * /usr/local/bin/backup-chroma.sh
```

Restoration:

```bash
aws s3 cp s3://scholarform-backups/chromadb/chroma-backup-<DATE>.tar.gz .
tar -xzf chroma-backup-<DATE>.tar.gz -C $CHROMA_PERSIST_DIR
```

### 5.3 Redis Persistence

Redis runs with both RDB (snapshot) and AOF (append-only file) persistence enabled.

- **RDB:** `save 3600 1 300 100 60 10000` — snapshot every hour if ≥1 key changed, every 5 minutes if ≥100 keys, every minute if ≥10000 keys.
- **AOF:** `appendfsync everysec` — fsync every second, balance of durability and performance.

In the event of Redis data loss, the system degrades gracefully but queued Celery tasks and SSE session state are lost. Redis is treated as a cache/queue broker, not a system of record.

### 5.4 Disaster Recovery Plan

> **See also:** [Disaster Recovery](DISASTER_RECOVERY.md)

**DR Tiers:**

| Tier | Scenario | RTO | RPO | Action |
| ------ | ---------- | ----- | ----- | -------- |
| 1 | Single container failure | < 5 min | — | Render auto-restarts |
| 2 | Availability zone failure | < 30 min | < 5 min | Render multi-region failover |
| 3 | Full region failure | < 4 hours | < 24 hours | Restore from S3 backups to new Render region |
| 4 | Data corruption | < 8 hours | < 24 hours | Point-in-time recovery from Supabase + ChromaDB backup |

### 5.5 RTO / RPO Targets

| Component | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
| ----------- | ------------------------------- | ------------------------------- |
| API Service | < 5 minutes | N/A (stateless) |
| PostgreSQL | < 1 hour | < 5 minutes (PITR) |
| ChromaDB | < 2 hours | < 24 hours |
| Redis | < 15 minutes | < 6 hours |
| Frontend (Vercel) | < 5 minutes | N/A (static deploy) |
| Full Stack | < 4 hours | < 24 hours |

---

## 6. Deployment

### 6.1 Deployment Windows

| Environment | Allowed Window | Approval | Notification |
| ------------- | --------------- | ---------- | -------------- |
| Development | Any time | Self-service | `#dev` Slack channel |
| Staging | Mon–Thu 08:00–20:00 UTC | CI passes | `#deployments` Slack channel |
| Production | Mon–Thu 10:00–16:00 UTC | PR review + CI + staging green | `#deployments` + `#incidents` Slack |

**Blackout periods:** No production deployments during:

- Major holidays (Christmas, New Year, etc.)
- Black Friday / peak usage periods (academic term start)
- Active incident resolution

### 6.2 Rollback Procedure

> **See also:** [Rollback Runbook](../runbooks/rollback.md)

Execute the rollback runbook immediately if:

- Error rate exceeds 5% within 10 minutes of deploy.
- Readiness endpoint becomes unhealthy.
- P0/P1 alert fires during the deploy observation window (15 minutes).

Rollback commands:

```bash
# Backend (Render)
render rollback --service scholarform-backend

# Frontend (Vercel)
vercel rollback --prod

# Database migration rollback
alembic downgrade -1
```

After rollback, verify health at `/api/v1/health/ready` and monitor error rate for 15 minutes.

### 6.3 Canary Strategy

Production deployments use Render's Blue-Green deployment model:

1. New version is deployed to a "green" instance.
2. Green instance health is verified via `/api/v1/health/ready`.
3. Traffic is gradually shifted: 10% → 50% → 100% over 15 minutes.
4. If error rate > 2% at any step, the canary is aborted and traffic shifts back to "blue."
5. Once 100% traffic is on green and stable for 15 minutes, the old blue instance is terminated.

### 6.4 Feature Flags

Feature flags are managed via environment variables in Render. Key flags:

| Flag | Default | Purpose |
| ------ | --------- | --------- |
| `ENHANCEMENT_QUEUE_ENABLED` | `false` | Enable Celery queue mode |
| `ENABLE_LLM_PDF_PARSER` | `false` | Enable LLMPDFParser PDF parser |
| `USE_LLM_CLASSIFICATION` | `false` | Enable LLMClassifier classification |
| `LLM_FALLBACK_ENABLED` | `true` | Allow fallback between LLM providers |
| `CLAMAV_ENABLED` | `true` | Enable ClamAV file scanning |
| `CACHE_ENABLED` | `true` | Enable Redis result caching |

Feature flag changes require a backend redeploy. Flags are toggled via Render environment variables or the admin API endpoint `/api/v1/admin/flags`.

---

## 7. On-Call

### 7.1 Shift Schedule

| Role | Schedule | Coverage |
|------|----------|----------|
| Primary On-Call | Weekly rotation, Mon 09:00 UTC → Mon 09:00 UTC | 24/7 |
| Secondary On-Call | Weekly rotation (offset from primary) | 24/7 |

**Rotation management:** PagerDuty manages the schedule. Calendar invites are synced from PagerDuty to Google Calendar.

**Holiday coverage:** Engineers can swap shifts with team members via PagerDuty. A minimum of 2 engineers must be designated on-call at all times.

### 7.2 Handoff Process

Handoff occurs every Monday at 09:00 UTC. The outgoing on-call must:

1. Summarize any ongoing incidents or investigations in `#on-call-handoff`.
2. Transfer any runbooks or documentation updates.
3. Confirm PagerDuty schedule reflects the new assignment.
4. Ensure the incoming on-call has access to all relevant credentials and dashboards.

Handoff template (posted in `#on-call-handoff`):

```
**On-Call Handoff — Week of YYYY-MM-DD**
Outgoing: @name
Incoming: @name

Active incidents: [none / link]
Ongoing investigations: [none / summary]
Runbook updates this week: [none / list]
Notes: [anything incoming should know]
```

### 7.3 Escalation Contacts

| Role | Contact | Escalation For |
| ------ | --------- | --------------- |
| Primary On-Call | PagerDuty schedule | All incidents |
| Secondary On-Call | PagerDuty schedule | P0 unacked > 15min |
| Engineering Lead | Slack @eng-lead | Cross-team coordination |
| Security Lead | Slack @security-lead | Security incidents |
| VP Engineering | Slack @vp-eng | Business continuity decisions |

### 7.4 Runbook References

During an incident, the on-call engineer should consult the relevant runbook:

| Situation | Runbook |
| ----------- | --------- |
| Service down / unreachable | [Service Down Runbook](../runbooks/service-down.md) |
| High error rate | [High Error Rate Runbook](../runbooks/high-error-rate.md) |
| High latency | [High Latency Runbook](../runbooks/high-latency.md) |
| Need to roll back deployment | [Rollback Runbook](../runbooks/rollback.md) |
| General incident response | [Incident Response Runbook](../runbooks/incident-response.md) |

---

## 8. Maintenance

### 8.1 Scheduled Maintenance Windows

| Window | Frequency | Scope | User Impact |
| -------- | ----------- | ------- | ------------- |
| Wed 02:00–04:00 UTC | Weekly | Database maintenance, dependency updates | None (graceful degradation) |
| Sat 04:00–06:00 UTC | Monthly | ChromaDB re-index, Redis defrag | Potential brief queue delay |
| Quarterly | Quarterly | Certificate rotation, dependency major upgrades | Scheduled downtime notice |

Maintenance windows are announced 72 hours in advance via the status page (`https://status.scholarform.ai`) and the `#maintenance` Slack channel.

### 8.2 Database Migration Process

Migrations use Alembic with the following procedure:

1. Add a new migration file: `alembic revision --autogenerate -m "description"`.
2. Review the generated migration carefully for data loss risks.
3. Test migration against a production-database clone in staging.
4. For large migrations (altering columns with > 1M rows), add a `--batch` flag to batch updates.
5. Deploy the migration as part of a backend deployment. The application reads from `alembic.ini`.
6. Monitor migration duration via the `alembic_migration_duration_seconds` metric.
7. If migration fails, rollback via `alembic downgrade -1` (see [Rollback Runbook](../runbooks/rollback.md)).

**Rollback safety:** All new migrations must include a `downgrade()` function. Migrations that drop columns must be split into two deploys: first deploy removes reads from the column, second deploy drops it.

### 8.3 Dependency Update Policy

| Category | Update Cadence | Responsibility | Testing Required |
| ---------- | --------------- | ---------------- | ----------------- |
| Security patches | Within 72 hours of CVE disclosure | DevOps | CI + staging |
| Patch versions | Weekly (Wed maintenance window) | DevOps | CI |
| Minor versions | Monthly | Engineering lead | CI + staging + QA |
| Major versions | Quarterly | Engineering lead | Full regression + staging |
| Python version (3.x) | Per release schedule | DevOps | Full test suite |
| Node.js version | Per LTS schedule | DevOps | Full test suite |

Dependencies are scanned weekly via Dependabot (GitHub) and `safety` (Python). Critical vulnerabilities trigger an immediate P3 alert.

### 8.4 Certificate Rotation

| Certificate | Renewal | Method | Responsible |
| ------------- | --------- | -------- | ------------- |
| API TLS (Render) | Automatic (Let's Encrypt) | Render auto-renewal | Render |
| Frontend TLS (Vercel) | Automatic | Vercel auto-renewal | Vercel |
| Custom domain certs | 90 days | Let's Encrypt via Certbot | DevOps |
| Internal service mTLS | Annual | Manual rotation via HashiCorp Vault | DevOps |

TLS certificate expiry is monitored via Prometheus `cert_expiry_days` metric with alerts at T-30 days (P3) and T-7 days (P2).

---

## 9. Runbooks Index

All runbooks are located in `docs/runbooks/` and are maintained by the DevOps team with quarterly review cadence.

| # | Runbook | Status | Description | Severity |
| --- | --------- | -------- | ------------- | ---------- |
| 1 | [Incident Response](../runbooks/incident-response.md) | ✅ Complete | Structured incident response from detection to postmortem | All |
| 2 | [Service Down](../runbooks/service-down.md) | ✅ Complete | P0 outage response for complete service unavailability | P0 |
| 3 | [High Error Rate](../runbooks/high-error-rate.md) | ✅ Complete | Elevated API error rates exceeding SLO thresholds | P1 |
| 4 | [High Latency](../runbooks/high-latency.md) | ✅ Complete | Elevated API response times exceeding SLO thresholds | P1 |
| 5 | [Rollback](../runbooks/rollback.md) | ✅ Complete | Deployment rollback for backend, frontend, and database | P0/P1 |
| 6 | [Branch Protection](../runbooks/branch-protection.md) | ✅ Complete | GitHub branch protection rules for main/develop | — |
| 7 | [Queue & Remote Offload Plan](../runbooks/queue-and-remote-offload-plan.md) | 📋 Planned | Future queue architecture for heavy document processing | — |

**Related documents:**

- [Disaster Recovery](DISASTER_RECOVERY.md)
- [Postmortem Template](../POSTMORTEM_TEMPLATE.md)
- [Deployment Guide](../deployment/Deployment.md)
- [Roadmap](../reports/ROADMAP.md)

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-07-21 | 1.0 | DevOps Team | Initial operations handbook |
