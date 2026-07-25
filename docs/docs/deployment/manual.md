# Manual Deployment

## Prerequisites

- Python 3.11+
- Node.js 20+
- Nginx (recommended for production)

## Backend

```bash
# Clone and setup
git clone https://github.com/amf/automated-manuscript-formatter.git
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
AMF_ENVIRONMENT=production
AMF_DEBUG=false
AMF_LOG_LEVEL=warning
AMF_ALLOWED_ORIGINS=https://your-domain.com
EOF

# Run with Gunicorn
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --access-logfile -
```

## Frontend

```bash
cd frontend
npm ci
npm run build

# Run with built-in server
npm start

# Or serve with PM2
npm install -g pm2
pm2 start npm --name amf-frontend -- start
```

## Nginx Reverse Proxy

```nginx
upstream amf-backend {
    server localhost:8000;
}

upstream amf-frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name amf.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name amf.example.com;

    ssl_certificate /etc/letsencrypt/live/amf.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/amf.example.com/privkey.pem;

    client_max_body_size 10M;

    location /api/ {
        proxy_pass http://amf-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://amf-frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Systemd Service

```ini
# /etc/systemd/system/amf-backend.service
[Unit]
Description=AMF Backend API
After=network.target

[Service]
Type=simple
User=amf
WorkingDirectory=/opt/amf/backend
ExecStart=/opt/amf/backend/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
