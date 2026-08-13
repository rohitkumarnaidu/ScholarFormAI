# Monitoring

This document details the monitoring strategy and infrastructure for ScholarForm AI. Monitoring ensures the reliability, availability, and performance of our services.

## Overview

ScholarForm AI uses a comprehensive monitoring stack based on **Prometheus** for metrics collection and **Grafana** for visualization. We monitor the following key components:
- **Next.js Frontend**: Web vitals, error rates, and API latency.
- **FastAPI Backend**: Endpoint latency, request rates, error codes, and active WebSockets.
- **Celery Workers**: Task queue length, processing time, success/failure rates.
- **Redis & PostgreSQL**: Cache hit rates, connection pools, and query performance.

## Metrics Architecture

1. **Prometheus Scrapers**: Prometheus polls the `/metrics` endpoint exposed by the FastAPI backend (using `prometheus-client`).
2. **Node Exporter**: Collects system-level metrics (CPU, Memory, Disk I/O) from host machines.
3. **Redis Exporter & Postgres Exporter**: Sidecar containers attached to our datastores to export DB-specific metrics.

## Key Dashboards

Our standard Grafana deployment includes the following dashboards:

### 1. Global Service Health
- **Total Requests / Sec**: Analyzed across all API routes.
- **Global Error Rate**: Aggregated HTTP 4xx and 5xx responses.
- **System Resource Utilization**: CPU and Memory across all containers.

### 2. AI Processing Pipeline
- **Agent Execution Time**: Time spent by the Forensic Auditor, Synthesis, and Layout agents.
- **LLM API Latency**: External API latency (Groq, NVIDIA).
- **Token Usage**: Token consumption rate per model.

### 3. Asynchronous Workers (Celery)
- **Queue Depth**: Number of pending formatting or generation tasks.
- **Worker Utilization**: Percentage of busy Celery workers.
- **Task Failure Rate**: See the [Runbooks](RUNBOOKS.md) for handling spikes.

## Alerting

Alertmanager is configured to route alerts to our Slack `#ops-alerts` channel and PagerDuty for critical severity.

- **Critical**: Database unreachable, 5xx rate > 5%, Celery queue depth > 1000 for 5 mins.
- **Warning**: High CPU usage (>80%), High memory usage (>85%), Token rate limit approaching.

## Cross-References
- [Observability Strategy](OBSERVABILITY.md)
- [System Performance](PERFORMANCE.md)
- [Incident Runbooks](RUNBOOKS.md)
