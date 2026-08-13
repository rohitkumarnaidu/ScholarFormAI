# Operational Runbooks

These runbooks provide step-by-step procedures for handling common incidents and system anomalies in the ScholarForm AI production environment.

## 🚨 Incident 1: High API Error Rate (5xx > 5%)

**Symptoms:** Alertmanager fires `HighApiErrorRate`. Users report UI failures.
**Immediate Actions:**
1. Check the Grafana Global Health Dashboard to identify the failing endpoints.
2. Check centralized logs (Loki/Elasticsearch) filtering for `level="ERROR"`.
3. Check database connectivity. If the database is unreachable, verify RDS/Postgres health.
**Resolution:**
- If due to bad deployment, initiate rollback via ArgoCD/GitHub Actions.
- If database connection pool is exhausted, restart the FastAPI pods to clear the pool and investigate connection leaks.

## 🚨 Incident 2: Celery Queue Backup

**Symptoms:** Alert `CeleryQueueDepthCritical` fires. Document formatting is taking too long.
**Immediate Actions:**
1. Check Grafana Asynchronous Workers dashboard. Are workers processing tasks, or are they hung?
2. If workers are processing but the queue is growing, we lack compute capacity.
**Resolution:**
- Scale the Celery worker deployment: `kubectl scale deployment celery-worker --replicas=10`
- If workers are hung (e.g., waiting indefinitely on an LLM API), check `OBSERVABILITY.md` traces. Ensure timeouts are configured correctly on the Groq/NVIDIA clients.

## 🚨 Incident 3: Redis Out of Memory (OOM)

**Symptoms:** Redis eviction rate spikes. Cache misses increase. Background tasks fail to enqueue.
**Immediate Actions:**
1. Connect to Redis and run `INFO memory` and `MEMORY DOCTOR`.
2. Identify the largest keys.
**Resolution:**
- If the queue is too large, see Incident 2.
- If cache keys (LLM responses) are consuming memory, adjust the TTL (Time to Live) configuration.
- Temporarily scale up the Redis instance class.

## 🚨 Incident 4: Third-Party LLM API Outage (Groq/NVIDIA)

**Symptoms:** Spikes in 502/504 errors on AI Generation endpoints.
**Immediate Actions:**
1. Check the status pages for Groq and NVIDIA.
**Resolution:**
- Update the configuration (`CONFIGURATION.md`) to failover to the secondary provider if implemented.
- Update the status page to notify users of degraded AI generation performance.
- Formatting tasks relying solely on layout agents should still function.

## Cross-References
- [Monitoring & Alerting](MONITORING.md)
- [Configuration](CONFIGURATION.md)
