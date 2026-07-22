<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# ScholarForm AI Docker Infrastructure

This directory contains the full local infrastructure stack for the backend.

Two Docker entry points exist on purpose:

- `backend/docker/docker-compose.yml`: lightweight backend-only stack for local API work.
- `backend/docker/docker-compose.yml`: fuller local stack with Grobid, Redis, ClamAV, and Celery workers.

Docker build files and monitoring configs are also split by purpose:

- `backend/docker/Dockerfile`: canonical backend image build file. CI and compose files should point here.
- `backend/docker/prometheus/prometheus.yml`: local development Prometheus config.
- `backend/ops/prometheus/prometheus.yml`: deployment or container-topology Prometheus config.

## Structure

- `docker-compose.yml`: fuller local infrastructure stack.
- `Dockerfile`: backend image build file used by the compose stacks and CI.
- `prometheus/`: Prometheus config for the local Docker stack.
- `grafana/`: Grafana dashboards for local monitoring.

## Quick Start

1. Change into this directory:

```bash
cd backend/docker
```

2. Start the full stack:

```bash
docker-compose up --build
```

3. Access services:

- Backend API: `http://localhost:8000`
- Grobid: `http://localhost:8070`
- Prometheus: `http://localhost:9090`

## Configuration

Environment variables are read from `../.env`.

Key variables:

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `OPENAI_API_KEY`
- `GROBID_URL`
- `CLAMAV_HOST`

## Maintenance

Reset volumes:

```bash
docker-compose down -v
```

View logs:

```bash
docker-compose logs -f
```
