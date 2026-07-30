<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Runbook: High Error Rate
description: P1 escalation for elevated API error rates exceeding SLO thresholds
sidebar_position: 3
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Runbook: High Error Rate

**Severity:** P1 (High)  
**Alert:** `ScholarFormHighErrorRate`  
**On-Call Response:** < 15 minutes

---

## Symptoms

- Error rate > 5% for > 5 minutes
- 5xx responses increasing
- User complaints about failed operations

---

## Immediate Actions

### 1. Identify the Failing Endpoint

```bash
# Check error rate by endpoint
curl -s "https://prometheus.scholarform.ai/api/v1/query?query=sum(rate(http_requests_total{job='scholarform',status=~'5..'}[5m])) by (path)"

# Check recent error logs
render logs --service scholarform-backend --tail 200 | grep -i "error\|exception\|traceback"
```

### 2. Common Causes & Fixes

#### LLM Provider Down

```bash
# Test provider connectivity
curl -s https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | head -c 200

# If provider is down, check circuit breaker status
# Circuit breakers should auto-trip and fallback to next tier
```

#### Database Connection Issues

```bash
# Check connection pool
psql $SUPABASE_DB_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'postgres'"

# If pool exhausted, restart connection pooler
# Supabase handles this automatically, but check status page
```

#### Rate Limiting Issues

```bash
# Check if rate limiter is misconfigured
# Look for 429 spikes vs 5xx spikes
render logs --service scholarform-backend --tail 100 | grep "429"
```

### 3. Mitigation

```bash
# If a specific endpoint is failing, consider temporary disable
# Add feature flag to disable failing feature

# Scale up if under heavy load
render deploy --service scholarform-backend --instance-type larger

# If bad deployment, rollback
render rollback --service scholarform-backend
```

---

## Post-Incident

1. Identify root cause from logs
2. Fix the issue or add circuit breaker
3. Update error handling to prevent recurrence
4. Write postmortem if error budget impacted
