<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Rollback Runbook
description: Deployment rollback procedures for backend and frontend
sidebar_position: 5
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Rollback Runbook

> **See also:** [Deployment Guide](../Deployment.md), [Disaster Recovery](../DISASTER_RECOVERY.md), [Incident Response](incident-response.md)

## Backend (Render)
1. Open the Render dashboard and select the backend service.
2. Navigate to the Deploys tab.
3. Select the last known good deploy and click Rollback.
4. Confirm the service is healthy at `/api/v1/health/ready`.

## Frontend (Vercel)
1. Open the Vercel dashboard and select the frontend project.
2. Locate the last known good deployment.
3. Click Promote to Production.
4. Verify the UI and API connectivity.

## Database Migrations (Alembic)
1. Connect to the backend environment.
2. Run `alembic downgrade -1` to revert the latest migration.
3. Confirm application health and database integrity.

## Feature Flags
1. Disable new features via environment flags (for example, disable enhancements or external integrations).
2. Redeploy the backend if needed.
3. Verify error rates and readiness status.
