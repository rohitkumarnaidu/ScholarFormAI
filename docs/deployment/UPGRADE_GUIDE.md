# Upgrade Guide

## Upgrading to v1.0.0

This is the initial release. No upgrade steps needed from prior versions.

## General Upgrade Steps

### Docker Deployments

```bash
# Pull latest images
docker compose pull

# Recreate containers
docker compose up -d

# Verify
curl http://localhost:8000/health
```

### Manual Deployments

```bash
# Backend
cd backend
git pull
pip install -r requirements.txt --upgrade
restart the backend service

# Frontend
cd frontend
git pull
npm ci
npm run build
restart the frontend service

# CLI
pip install amf-cli --upgrade

# SDK
pip install amf-sdk --upgrade
```

## Pre-Upgrade Checklist

- [ ] Read the CHANGELOG for breaking changes
- [ ] Back up configuration files
- [ ] Test upgrade in staging environment
- [ ] Verify all services are healthy after upgrade
- [ ] Test formatting with representative manuscripts

## Rollback

### Docker

```bash
# Rollback to previous version
docker compose down
git checkout v0.x.x
docker compose up -d
```

### Manual

```bash
# Reinstall previous version
pip install amf-cli==0.x.x
```
