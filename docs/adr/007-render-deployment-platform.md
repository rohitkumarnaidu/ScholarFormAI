<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 007: Render as Deployment Platform"
description: Decision to use Render Web Services for backend hosting
sidebar_position: 46
version: "1.0"
status: ✅ Accepted
owner: DevOps Team
review_cadence: never
last_updated: June 2026
---

# ADR 007: Render as Deployment Platform

## Context

The application requires a hosting platform that supports Python (FastAPI), Node.js (Next.js), Redis, and background workers without complex Kubernetes infrastructure.

## Decision

Deploy on Render:

| Component | Render Service | Plan |
|-----------|---------------|------|
| Backend API | Web Service (Gunicorn + Uvicorn) | Starter |
| Frontend | Static Site / Web Service | Free |
| Celery Worker | Background Worker | Starter |
| Redis | Managed Redis | Starter |

## Consequences

- Automatic HTTPS and custom domain support
- Deploy hooks from GitHub for CI/CD
- 512MB RAM limit per service (influences GROBID and AI model decisions)
- No native Kubernetes or advanced orchestration
- Render's internal networking for service-to-service communication
