<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Incident Response Runbook
description: Structured incident response procedures from detection to postmortem
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Incident Response Runbook

> **See also:** [Postmortem Template](../POSTMORTEM_TEMPLATE.md), [Disaster Recovery](../DISASTER_RECOVERY.md), [Runbooks](.)

## Alert Matrix
- 5xx error rate > 1% for 5 minutes.
- p95 latency > 1s for 5 minutes.
- `celery_queue_depth` > 100 for 10 minutes.
- LLM failure spikes or `llm_request_duration_seconds` p95 > 10s for 10 minutes.
- SSE/WS active connections drop unexpectedly.
- ClamAV scan failures or `clamav_scan_duration_seconds` p95 > 5s for 10 minutes.
- Readiness endpoint `/api/v1/health/ready` unhealthy for 5 minutes.

## Response Playbooks
### 5xx Error Rate
Immediate actions: Check deploy status, inspect error logs, verify DB health, confirm Redis/Grobid/LLM availability.
Escalation: On-call engineer, backend lead, infra lead.
Verify resolution: Error rate < 1% for 10 minutes, readiness healthy.

### High Latency
Immediate actions: Check queue depth, check CPU/memory, inspect slow endpoints, verify external dependencies.
Escalation: On-call engineer, performance owner.
Verify resolution: p95 latency < 1s for 10 minutes.

### Queue Depth Backlog
Immediate actions: Verify Celery workers are running, scale workers, check broker health.
Escalation: On-call engineer, infra lead.
Verify resolution: `celery_queue_depth` back under 50 for 10 minutes.

### LLM Failures or Slow LLM
Immediate actions: Check provider status, fail over to alternate model, review API key limits, reduce concurrency if needed.
Escalation: On-call engineer, ML lead.
Verify resolution: LLM failure rate stabilized, p95 latency < 10s for 10 minutes.

### Realtime Connection Drops
Immediate actions: Check Redis pub/sub health, review recent deploys, verify WebSocket/SSE proxies.
Escalation: On-call engineer, infra lead.
Verify resolution: SSE/WS active connections stable and reconnect proxy returns to baseline.

### ClamAV Scan Failures
Immediate actions: Check ClamAV daemon health, verify network connectivity, temporarily disable AV if blocking uploads.
Escalation: On-call engineer, security lead.
Verify resolution: Scan duration p95 < 5s and failures resolved for 10 minutes.

### Readiness Unhealthy
Immediate actions: Identify failing dependency in readiness payload, restart unhealthy services.
Escalation: On-call engineer, infra lead.
Verify resolution: `/api/v1/health/ready` returns 200 for 10 minutes.
