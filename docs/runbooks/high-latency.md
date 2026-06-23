<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Runbook: High Latency
description: P1 escalation for elevated API response times exceeding SLO thresholds
sidebar_position: 4
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Runbook: High Latency
**Severity:** P1 (High)  
**Alert:** `ScholarFormHighLatency`  
**On-Call Response:** < 15 minutes

---

## Symptoms
- p95 latency > 5s for > 5 minutes
- Users experiencing slow responses
- Timeout errors increasing

---

## Immediate Actions

### 1. Identify Slow Endpoints
```bash
# Check latency by endpoint
curl -s "https://prometheus.scholarform.ai/api/v1/query?query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job='scholarform'}[5m]))"

# Check for slow database queries
psql $SUPABASE_DB_URL -c "SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10"
```

### 2. Common Causes & Fixes

#### LLM Provider Slow
```bash
# Check provider response times
# If user API keys are being used, check their rate limits
# Provider may be throttling

# Mitigation: Switch to fallback provider
# Circuit breakers should handle this automatically
```

#### Database Slow Queries
```bash
# Check for long-running queries
psql $SUPABASE_DB_URL -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 10"

# Kill long-running queries if needed
psql $SUPABASE_DB_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '30 seconds'"
```

#### Memory Pressure
```bash
# Check memory usage
render metrics --service scholarform-backend --metric memory

# If memory high, restart service
render deploy --service scholarform-backend
```

### 3. Mitigation
```bash
# Enable query caching if not already
# Reduce payload sizes
# Add timeout to slow operations
```

---

## Post-Incident
1. Optimize slow queries or add indexes
2. Add caching for frequently accessed data
3. Review timeout configurations
4. Update this runbook if new patterns found
