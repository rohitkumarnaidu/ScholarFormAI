<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — SLO Definitions
description: Service level objectives, error budgets, and monitoring thresholds
sidebar_position: 38
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — SLO Definitions

---

## Service Level Objectives (SLOs)

### 1. Availability SLO
| Metric | Target | Window | Measurement |
|--------|--------|--------|-------------|
| API Uptime | 99.9% | 30-day rolling | `/api/v1/health/live` returns 200 |
| Frontend Uptime | 99.95% | 30-day rolling | Next.js server responds |
| Database Availability | 99.99% | 30-day rolling | Supabase connection pool healthy |

**Error Budget:** 43.2 minutes/month downtime allowed

### 2. Latency SLO
| Endpoint | p50 | p95 | p99 |
|----------|-----|-----|-----|
| Health checks | < 10ms | < 50ms | < 100ms |
| Document upload | < 500ms | < 2s | < 5s |
| Document processing | < 5s | < 30s | < 60s |
| Template rendering | < 200ms | < 1s | < 3s |
| API key operations | < 100ms | < 500ms | < 1s |
| LLM proxy (user keys) | < 1s | < 5s | < 15s |

**Error Budget:** 5% of requests may exceed p95 target

### 3. Throughput SLO
| Metric | Target | Peak |
|--------|--------|------|
| Requests/second | 100 | 500 |
| Concurrent users | 1,000 | 5,000 |
| Documents processed/hour | 500 | 2,000 |

### 4. Data Integrity SLO
| Metric | Target |
|--------|--------|
| Data loss | 0 (zero tolerance) |
| Backup RPO | 1 hour |
| Backup RTO | 4 hours |
| Migration success rate | 100% |

### 5. Security SLO
| Metric | Target |
|--------|--------|
| Critical vulnerability response | < 24 hours |
| High vulnerability response | < 72 hours |
| Auth failure rate | < 0.1% |
| Rate limit bypass | 0 (zero tolerance) |

---

## Error Budget Policy

| Budget Remaining | Action |
|-----------------|--------|
| > 50% | Normal development velocity |
| 25-50% | Increased monitoring, review recent incidents |
| 10-25% | Freeze non-critical features, focus on reliability |
| < 10% | Feature freeze, all-hands on reliability |
| 0% | Incident response mode, postmortem required |

---

## Alerting Thresholds

| Severity | Condition | Response Time |
|----------|-----------|---------------|
| P0 (Critical) | Service down, data loss | < 5 minutes |
| P1 (High) | Error rate > 5%, latency > 2x p95 | < 15 minutes |
| P2 (Medium) | Error rate > 1%, latency > 1.5x p95 | < 1 hour |
| P3 (Low) | Degraded performance, non-critical feature down | < 4 hours |

---

## Dashboard Links

> **Note:** These dashboards are planned for Phase 5 deployment and are not yet live.

- **Grafana:** `https://grafana.scholarform.ai/d/scholarform` *(not yet deployed)*
- **Prometheus:** `https://prometheus.scholarform.ai` *(not yet deployed)*
- **Uptime:** `https://status.scholarform.ai` *(not yet deployed)*
- **Error Budget:** `https://grafana.scholarform.ai/d/error-budget` *(not yet deployed)*
