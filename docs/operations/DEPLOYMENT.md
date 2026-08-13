# Deployment Guide

ScholarForm AI is containerized and designed for cloud-native deployment. This guide covers the production deployment strategy.

## Architecture

Our production topology consists of:
- **Load Balancer**: Nginx / AWS ALB
- **Frontend**: Next.js Node server
- **Backend API**: FastAPI (Uvicorn + Gunicorn)
- **Workers**: Celery workers
- **Database**: Managed PostgreSQL (e.g., AWS RDS)
- **Cache / Broker**: Managed Redis (e.g., AWS ElastiCache)

## Docker Compose (Single Node)

For smaller deployments or staging, Docker Compose is sufficient.

```bash
# Start all services detached
docker compose -f deploy/services/docker-compose.yml up -d --build

# Scale Celery workers
docker compose -f deploy/services/docker-compose.yml up -d --scale celery_worker=3
```

## Kubernetes (Multi-Node)

For high-availability production environments, we recommend Kubernetes.

1. **Helm Charts**: (Located in `deploy/helm/`) apply configurations for deployments, services, and ingresses.
2. **Autoscaling (HPA)**: Both the FastAPI pods and Celery workers are configured for Horizontal Pod Autoscaling based on CPU utilization and queue depth (using KEDA).

## CI/CD Pipeline

We use GitHub Actions for our CI/CD workflow:
1. **Lint & Test**: Runs `ruff`, `pytest`, `eslint`, and `jest` on every PR.
2. **Build**: Builds Docker images and pushes to Amazon ECR / Docker Hub upon merge to `main`.
3. **Deploy**: Triggers a deployment webhook or updates Kubernetes manifests via GitOps (ArgoCD).

## Security Best Practices (SLSA 3)

- **Minimal Images**: We use Alpine or distroless base images.
- **Non-Root Users**: All containers run as a non-root user.
- **Image Scanning**: Images are scanned with Trivy during the CI build process.

## Cross-References
- [Configuration](CONFIGURATION.md)
- [Monitoring](MONITORING.md)
- [Observability](OBSERVABILITY.md)
