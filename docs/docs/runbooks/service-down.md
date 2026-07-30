<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Runbook: Service Down
description: P0 outage response procedures for complete service unavailability
sidebar_position: 2
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Runbook: Service Down
**Severity:** P0 (Critical)  
**Alert:** `ScholarFormServiceDown`  
**On-Call Response:** < 5 minutes

> **See also:** [Disaster Recovery](../DISASTER_RECOVERY.md), [Incident Response](incident-response.md), [Rollback](rollback.md)

---

## Symptoms
- `up{job="scholarform"} == 0` for > 2 minutes
- Health endpoint `/api/v1/health/live` not responding
- Users see 502/503 errors

---

## Immediate Actions

### 1. Verify the Outage
```bash
# Check if the service is responding
curl -s -o /dev/null -w "%{http_code}" https://api.scholarform.ai/api/v1/health/live

# Check Render dashboard
open https://dashboard.render.com/web/scholarform-backend

# Check logs
render logs --service scholarform-backend --tail 100
```

### 2. Check Infrastructure
```bash
# Check if Render is having issues
curl -s https://status.render.com | grep -i "operational"

# Check database connectivity
psql $SUPABASE_DB_URL -c "SELECT 1"

# Check Redis connectivity
redis-cli -u $REDIS_URL ping
```

### 3. Restart Service
```bash
# Via Render dashboard: click "Manual Deploy" → "Clear build cache and deploy"
# Or via CLI:
render deploy --service scholarform-backend
```

### 4. If Restart Fails
```bash
# Check for OOM kills
render logs --service scholarform-backend --tail 500 | grep -i "oom\|killed\|memory"

# Check for migration failures
render logs --service scholarform-backend --tail 500 | grep -i "migration\|alembic\|error"

# Rollback to last known good deployment
render rollback --service scholarform-backend
```

---

## Root Cause Analysis

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| OOM kills | Memory leak, large document | Increase memory limit, add streaming |
| Migration failure | Schema conflict | Fix migration, rollback, re-apply |
| DB connection timeout | Supabase outage | Check Supabase status, retry |
| Redis timeout | Redis down or network | Check Redis status, fallback to memory |
| Build failure | Dependency issue | Pin versions, clear cache |

---

## Communication
1. Post incident in `#incidents` Slack channel
2. Update status page: `https://status.scholarform.ai`
3. Notify affected users if outage > 15 minutes

---

## Post-Incident
1. Write postmortem within 48 hours
2. Add monitoring for the failure mode
3. Update this runbook if new steps discovered
