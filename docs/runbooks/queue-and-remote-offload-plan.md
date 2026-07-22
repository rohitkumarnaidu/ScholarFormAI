<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Queue and Remote Offload Plan (Deferred)
description: Future queue-based architecture for heavy document processing tasks
sidebar_position: 7
version: "1.0"
status: 📋 Planned
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Queue and Remote Offload Plan (Deferred)

> **See also:** [Roadmap](../Roadmap.md), [Deployment Guide](../Deployment.md)

This document captures deferred work. It does not enable queue mode or Nougat/SciBERT paths yet.

## Phase 2: Queue Mode (No Code Change Now)

Current status:

- `ENHANCEMENT_QUEUE_ENABLED=false`
- Queue mode remains off for free-tier stability.

Readiness package (to execute later):

1. Deploy one dedicated Celery worker process from `backend/app/tasks/celery_tasks.py`.
2. Deploy one scheduler/beat process for periodic jobs.
3. Keep Redis as broker and result backend.
4. Confirm worker and beat uptime for 7 days before turning queue on.

Activation gate:

- Enable queue mode only after:
  - No backend OOM incidents
  - No deploy health-check timeouts
  - Stable Redis connectivity

## Phase 3: Nougat and SciBERT Remote Offload Design

Current status:

- `ENABLE_NOUGAT_PARSER=false`
- `USE_SCIBERT_CLASSIFICATION=false`

Design targets for next code phase:

1. Add Nougat remote envs:
   - `NOUGAT_URLS`
   - `NOUGAT_HEALTH_PATH`
2. Add SciBERT remote envs:
   - `SCIBERT_URLS`
   - `SCIBERT_HEALTH_PATH`
3. Implement URL-list precedence:
   - `*_URLS` first, fallback to single URL if list is empty.
4. Implement retry and failover behavior:
   - Per-endpoint bounded retries
   - Primary to shadow failover
   - Short-lived cache of last-good endpoint
5. Add keepalive coverage:
   - Primary and shadow secrets for Nougat/SciBERT
   - Scheduled health probing with timeout caps

Safety policy:

- Keep both toggles false by default until endpoint SLA is proven.
