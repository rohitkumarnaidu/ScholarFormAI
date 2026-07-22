<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Risk Register
description: Risk inventory, severity ratings, and mitigation strategies
sidebar_position: 37
version: "1.0"
status: 🔄 In Progress
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — Risk Register

> **See also:** [Security](Security.md), [Deployment](Deployment.md), [SLO Definitions](SLO_DEFINITIONS.md)

## High Risks

| ID | Risk | Current State | Mitigation |
|---|---|---|---|
| R-01 | Render free-tier memory pressure (512MB) | Active architectural constraint | Low-memory profile is enforced (`LOW_MEMORY_MODE=true`, `PRELOAD_AI_MODELS=false`, `RAG_USE_TRANSFORMERS=false`) |
| R-02 | Upstream HF instability (timeouts, 502, partial payloads) | Active external dependency risk | Primary/shadow routing + failover for GROBID, plus scheduled keepalive checks for all service pairs |
| R-03 | Production deploy hangs on unhealthy backend | Previously observed | Manual deploy workflow gates frontend deploy on backend `/api/v1/health/live` |
| R-04 | Queue mode can increase memory and failure surface on free tier | Intentionally deferred | Keep `ENHANCEMENT_QUEUE_ENABLED=false` until 7-day stability window is met |

## Medium Risks

| ID | Risk | Current State | Mitigation |
|---|---|---|---|
| R-05 | DB connectivity instability or temporary Supabase outages | Intermittent external risk | Health endpoints use degraded-mode handling; retries and structured logs are enabled |
| R-06 | OCR/parser quality variability across remote services | Active quality risk | Multi-service topology with health probes; fallback chain remains available |
| R-07 | Missing deep observability in some environments | Partial | Structured logging enabled; keep Prometheus/Grafana dashboards in repo and deploy where needed |
| R-08 | Deployment knowledge drift in docs/secrets | Ongoing maintenance risk | Keep deployment docs aligned with active workflows and secret names |

## Low Risks

| ID | Risk | Current State | Mitigation |
|---|---|---|---|
| R-09 | Temporary file accumulation | Controlled | `ENABLE_FILE_CLEANUP=true` with retention policy |
| R-10 | Feature drift for Nougat/SciBERT paths | Controlled by default-off policy | Keep both toggles off until remote endpoint SLA is proven |

## Notes

- No automatic staging workflow is required for this phase; production remains manual by design.
- This register reflects strict `$0` operation goals.
