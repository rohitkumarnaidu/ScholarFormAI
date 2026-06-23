<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 006: Celery for Background Task Processing"
description: Decision to use Celery with Redis broker for async task execution
sidebar_position: 45
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: June 2026
---

# ADR 006: Celery for Background Task Processing

## Context

Document formatting, AI generation, and synthesis are long-running operations that cannot block the HTTP request-response cycle.

## Decision

Use Celery with Redis as the message broker to handle background tasks. Two task queues exist:

- `interactive` — short tasks (preview rendering, status updates)
- `batch` — long-running tasks (document formatting, AI generation, synthesis)

## Consequences

- Worker processes are separate from the web server (horizontal scaling possible)
- Redis doubles as the result backend and cache layer
- Requires a separate Celery worker process in production
- Task state is polled via REST endpoints (no WebSocket for job progress in formatter pipeline)
