# Docker Deployment

## Prerequisites

- Docker 24.0+
- Docker Compose v2.20+

## Quick Start

```bash
git clone https://github.com/amf/automated-manuscript-formatter.git
cd automated-manuscript-formatter
docker compose up -d
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 8000 | FastAPI backend |
| `frontend` | 3000 | Next.js web UI |
| `docs` | 8080 | Documentation site |

## Production Deployment

### Using a `.env` file

```bash
# .env
AMF_ENVIRONMENT=production
AMF_DEBUG=false
AMF_LOG_LEVEL=warning
AMF_SECRET_KEY=your-production-secret-key
AMF_ALLOWED_ORIGINS=https://your-domain.com
```

### With Nginx

```nginx
server {
    listen 80;
    server_name amf.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name amf.example.com;

    ssl_certificate /etc/letsencrypt/live/amf.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/amf.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        client_max_body_size 10M;
    }
}
```

## Scaling

```bash
# Scale backend for more throughput
docker compose up -d --scale backend=3

# With load balancer (add to docker-compose.yml)
services:
  lb:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

## Monitoring

```bash
# View logs
docker compose logs -f backend

# Health check
curl http://localhost:8000/health

# Resource usage
docker stats
```
