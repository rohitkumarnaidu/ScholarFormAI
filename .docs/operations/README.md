---
title: ScholarForm AI — Operations
description: Infrastructure overview, monitoring stack, and operational procedures
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: DevOps
review_cadence: monthly
last_updated: June 2026
---

# Operations

## Infrastructure

| Component | Provider | Tier | Notes |
|-----------|----------|------|-------|
| Frontend | Vercel | Free (Hobby) | SSR, edge functions |
| Backend | Render | Free (Web Service) | 512MB RAM, cold starts |
| Database | Supabase | Free | PostgreSQL, 500MB |
| Cache/Queue | Upstash Redis | Free | 10MB |
| Vector DB | ChromaDB | Co-located | Same container as backend |
| PDF Parsing | Docling or PyMuPDF | In-process | GROBID optional (Docker) |
| LLM | NVIDIA NIM | Free tier | Fallback: Groq then Ollama |

## Available Documents

| Document | Description |
|----------|-------------|
| [Disaster Recovery](../docs/DISASTER_RECOVERY.md) | DR procedures with RTO and RPO targets |
| [Monitoring & Alerting](monitoring.md) | Prometheus, Grafana, and Sentry configuration |
| [Performance Benchmarks](performance-benchmarks.md) | Load test results and capacity planning |
| [Infrastructure Setup](content/Deployment & Operations/Infrastructure Setup.md) | Infrastructure provisioning guide |

## Monitoring Stack

- **Application Metrics**: Prometheus endpoint at `/api/v1/metrics`
- **Dashboards**: Grafana (pipeline.json, system metrics)
- **Error Tracking**: Sentry (frontend and backend)
- **Health Checks**: `/api/v1/health` and `/api/v1/ready`
- **Uptime Monitoring**: Render built-in health checks

## See Also

- [Operations Runbooks](../runbooks/)
- [Deployment & Operations Docs](content/Deployment & Operations/Deployment & Operations.md)
