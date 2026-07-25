# Docker Deployment

## Quick Start

```bash
git clone https://github.com/amf/automated-manuscript-formatter.git
cd automated-manuscript-formatter
docker compose up -d
```

## Production

Create `docker-compose.override.yml`:

```yaml
services:
  backend:
    environment:
      - AMF_ENVIRONMENT=production
      - AMF_DEBUG=false
      - AMF_LOG_LEVEL=warning
      - AMF_ALLOWED_ORIGINS=https://your-domain.com
    restart: always
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  frontend:
    restart: always
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
```

## Scaling

```bash
# Scale backend for more throughput
docker compose up -d --scale backend=3

# With Nginx load balancer
docker compose -f docker-compose.yml -f docker-compose.lb.yml up -d
```

## Health Checks

```bash
# Check all services
docker compose ps

# View logs
docker compose logs -f backend

# Health endpoint
curl http://localhost:8000/health
```
