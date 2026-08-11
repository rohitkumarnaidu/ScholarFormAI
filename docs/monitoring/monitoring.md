<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Monitoring & Alerting
description: Prometheus metrics, Grafana dashboards, and alert rules
sidebar_position: 2
version: "1.0"
status: ✅ Complete
owner: DevOps
review_cadence: monthly
last_updated: July 2026
---

# Monitoring & Alerting

## Metrics Endpoints

| Endpoint | Type | Description |
| ---------- | ------ | ------------- |
| `/api/v1/health` | JSON | Component health (DB, Redis, ChromaDB, LLM) |
| `/api/v1/ready` | JSON | Readiness probe for load balancers |
| `/api/v1/metrics` | Prometheus | Prometheus-formatted metrics |

## Key Metrics

| Metric | Type | Labels | Description |
| -------- | ------ | -------- | ------------- |
| `http_requests_total` | Counter | method, endpoint, status | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request latency |
| `pipeline_jobs_total` | Counter | stage, status | Pipeline job counts |
| `pipeline_job_duration_seconds` | Histogram | stage | Pipeline stage duration |
| `llm_requests_total` | Counter | provider, model | LLM API call counts |
| `llm_request_duration_seconds` | Histogram | provider | LLM response time |

## Monitoring Pipeline

```mermaid
sequenceDiagram
    participant App as "FastAPI App"
    participant Prom as "Prometheus"
    participant Graf as "Grafana"
    participant Alert as "Alert Manager"
    App->>Prom: /api/v1/metrics
    Prom->>Graf: Metrics data
    Graf->>Alert: Threshold breach
    Alert-->>App: Alert notification
    Note over App,Alert: Metrics: 15s scrape interval<br/>Alerts: evaluated every 1m
```

## Alert Rules

| Alert | Condition | Severity | Response |
| ------- | ----------- | ---------- | ---------- |
| High Error Rate | Error ratio > 5% over 5 minutes | P1 | Check recent deploys |
| High Latency | p95 > 1s over 5 minutes | P2 | Investigate bottleneck |
| Low Disk Space | Disk < 10% free | P2 | Clean up or scale |
| Pipeline Failure Rate | Failure rate > 10% | P1 | Check pipeline stages |
| LLM Provider Down | More than 50% errors from provider | P2 | Trigger fallback |

## Grafana Dashboards

- **Pipeline Dashboard**: `backend/docker/grafana/dashboards/pipeline.json`
- **System Metrics**: CPU, memory, disk, network
- **Business Metrics**: Documents processed, users, error rates

## See Also

- [Health & Metrics Docs](../backend/Monitoring & Metrics.md)
- [Operations Runbooks](../runbooks/)
- [Deployment & Operations](../docs/knowledge/Deployment & Operations/Monitoring & Alerting.md)
