# Deployment Guide

## Docker Compose (Recommended)

The simplest way to deploy AMF:

```bash
# Clone and deploy
git clone https://github.com/amf/automated-manuscript-formatter.git
cd automated-manuscript-formatter
docker compose up -d
```

Services will be available at:
- **Web UI**: http://localhost:3000
- **API**: http://localhost:8000
- **Docs**: http://localhost:8080

### Production Configuration

Create a `.env` file:

```env
AMF_ENVIRONMENT=production
AMF_DEBUG=false
AMF_LOG_LEVEL=warning
AMF_SECRET_KEY=generate-a-strong-secret-key
AMF_ALLOWED_ORIGINS=https://your-domain.com
```

```yaml
# docker-compose.override.yml
services:
  backend:
    environment:
      - AMF_ENVIRONMENT=production
      - AMF_DEBUG=false
    restart: always
```

## Manual Deployment

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt

# Production with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Frontend (Next.js)

```bash
cd frontend
npm ci
npm run build
npm start
```

### Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name amf.example.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 10M;
    }
}
```

## Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amf-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: amf-backend
  template:
    metadata:
      labels:
        app: amf-backend
    spec:
      containers:
      - name: backend
        image: ghcr.io/amf/backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: AMF_ENVIRONMENT
          value: "production"
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Cloud Platforms

### AWS ECS

1. Build Docker images and push to ECR
2. Create ECS task definitions with environment variables
3. Set up ALB with SSL termination
4. Configure auto-scaling

### Google Cloud Run

```bash
gcloud run deploy amf-backend \
  --image ghcr.io/amf/backend:latest \
  --set-env-vars AMF_ENVIRONMENT=production \
  --memory 512Mi \
  --cpu 1 \
  --port 8000
```

### Azure Container Apps

```bash
az containerapp create \
  --name amf-backend \
  --image ghcr.io/amf/backend:latest \
  --environment-vars AMF_ENVIRONMENT=production \
  --ingress external \
  --target-port 8000
```

## Scaling

### Horizontal Scaling

- Backend API scales horizontally (stateless)
- Frontend can be served via CDN
- Use a load balancer for distribution

### Vertical Scaling

- Increase memory for large manuscript processing
- Increase CPU for concurrent formatting requests

## Backup and Recovery

- Back up configuration and templates
- Store uploaded files in persistent storage (S3, volumes)
- Database backups (when database is added)
