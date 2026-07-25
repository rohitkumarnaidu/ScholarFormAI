# Update Management — Deployment Guide

## Overview

This guide covers deploying AMF with the update management system in production environments. Topics include air-gapped deployments, custom update servers, CI/CD integration, and monitoring.

## Deployment Scenarios

### Scenario 1: Standard (GitHub Releases)

The default configuration connects to GitHub Releases. Recommended for most deployments.

```yaml
# docker-compose.yml
services:
  backend:
    image: amf/backend:latest
    environment:
      - UPDATE_REPO_OWNER=amf
      - UPDATE_REPO_NAME=automated-manuscript-formatter
      - UPDATE_CHANNEL=stable
      - UPDATE_CHECK_INTERVAL=24
    volumes:
      - amf_data:/home/amf/.amf
```

### Scenario 2: Air-Gapped / Offline

For environments without internet access, deploy a local update server or distribute updates manually.

```bash
# On an internet-connected machine, download updates
amf update download --version 1.2.0

# Copy the downloaded file to the air-gapped system
scp ~/.amf/updates/amf-1.2.0.zip user@airgap:/tmp/

# On the air-gapped system, install from file
amf update install --source /tmp/amf-1.2.0.zip
```

### Scenario 3: Self-Hosted Update Server

Host your own update server behind a private network.

```python
# custom_update_source.py
# Extend UpdateService to use your own API
class CustomUpdateService(UpdateService):
    def _fetch_releases(self) -> list[dict]:
        url = "https://updates.internal.example.com/api/releases"
        with httpx.Client() as client:
            resp = client.get(url, headers={"Authorization": "Bearer TOKEN"})
            resp.raise_for_status()
            return resp.json()
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `UPDATE_REPO_OWNER` | `amf` | GitHub repository owner |
| `UPDATE_REPO_NAME` | `automated-manuscript-formatter` | GitHub repository name |
| `UPDATE_CHANNEL` | `stable` | Default release channel |
| `UPDATE_CHECK_INTERVAL` | `24` | Hours between checks |
| `UPDATE_AUTO_DOWNLOAD` | `false` | Auto-download updates |
| `UPDATE_AUTO_INSTALL` | `false` | Auto-install updates |
| `UPDATE_GITHUB_TOKEN` | — | GitHub API token |
| `UPDATE_PROXY_URL` | — | HTTP proxy for downloads |
| `UPDATE_DIR` | `~/.amf/updates` | Update storage directory |
| `UPDATE_VERIFY_CHECKSUM` | `true` | Verify file checksums |
| `UPDATE_VERIFY_SIGNATURE` | `true` | Verify GPG signatures |

## Docker Deployment

### Building with Update Support

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e backend/ -e cli/
# Ensure update directories exist
RUN mkdir -p /root/.amf/updates/backups
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose with Update Service

```yaml
version: "3.8"
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - amf_data:/root/.amf
    environment:
      - UPDATE_CHANNEL=stable
      - UPDATE_AUTO_CHECK=true
      - UPDATE_GITHUB_TOKEN=${GITHUB_TOKEN:-}

  frontend:
    build: frontend/
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api/v1

volumes:
  amf_data:
```

## Kubernetes Deployment

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: amf-update-config
data:
  UPDATE_CHANNEL: "stable"
  UPDATE_CHECK_INTERVAL: "24"
  UPDATE_AUTO_CHECK: "true"
  UPDATE_VERIFY_CHECKSUM: "true"
```

### Persistent Volume for Update Data

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: amf-update-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### Deployment with Update Volume

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: amf-backend
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: backend
          image: amf/backend:latest
          envFrom:
            - configMapRef:
                name: amf-update-config
          volumeMounts:
            - name: update-data
              mountPath: /root/.amf
      volumes:
        - name: update-data
          persistentVolumeClaim:
            claimName: amf-update-pvc
```

## CI/CD Integration

### GitHub Actions — Automated Release Publishing

```yaml
name: Publish Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build packages
        run: |
          pip install build
          python -m build backend/
          python -m build cli/

      - name: Generate checksums
        run: |
          sha256sum dist/*.tar.gz dist/*.whl > dist/checksums.txt

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/*
          body_path: CHANGELOG.md
          prerelease: ${{ contains(github.ref, '-beta') || contains(github.ref, '-rc') }}
```

### Automated Update Testing

```yaml
name: Test Update Flow
on:
  schedule:
    - cron: '0 6 * * *'  # Daily

jobs:
  test-update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Test update check
        run: |
          pip install -e backend/ -e cli/
          amf update check --channel stable

      - name: Test download
        run: amf update download

      - name: Test rollback
        run: amf update rollback
```

## Monitoring

### Prometheus Metrics

The update system exposes metrics through the telemetry system:

```
# HELP amf_update_check_total Total update checks
# TYPE amf_update_check_total counter
amf_update_check_total{status="success"} 42
amf_update_check_total{status="error"} 3

# HELP amf_update_download_total Total update downloads
# TYPE amf_update_download_total counter
amf_update_download_total{success="true"} 5

# HELP amf_current_version Current application version
# TYPE amf_current_version gauge
amf_current_version{version="1.0.0"} 1
```

### Health Checks

The update system contributes to the `/health/detailed` endpoint:

```json
{
  "updates": {
    "status": "healthy",
    "current_version": "1.0.0",
    "last_check": "2026-07-25T10:00:00Z",
    "updates_available": false,
    "history_count": 3
  }
}
```

## Security Considerations

### Rate Limiting

- Unauthenticated GitHub API: 60 req/h (may cause false negatives in update checks)
- Solution: Set `github_token` in settings or configure a self-hosted update server

### Checksum Verification

- Always enabled by default
- SHA256 verification prevents tampered downloads
- Mismatches are logged but installation is not blocked (configurable)

### Proxy Configuration

- Use `proxy_url` setting for enterprise firewall environments
- Supports HTTP/HTTPS proxies
- SOCKS proxies are not supported

## Backup and Recovery

### Automatic Backups

Each installation creates a timestamped backup:

```
~/.amf/updates/backups/
├── v1.0.0/
│   ├── app/
│   ├── cli/
│   └── sdk/
├── v1.1.0/
│   └── ...
```

### Manual Backup

```bash
# Manually backup before major update
cp -r /opt/amf /opt/amf-backup-$(date +%Y%m%d)

# Restore from manual backup
cp -r /opt/amf-backup-20260725/* /opt/amf/
```
