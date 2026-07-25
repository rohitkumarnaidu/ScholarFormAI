# Migration Guide

## v0.x → v1.0.0

### Breaking Changes

- Initial release — no prior versions to migrate from.

### API Changes

- All endpoints now under `/api/v1/` prefix
- Request/response formats follow v1 schemas

### Configuration Changes

- Environment variables now use `AMF_` prefix
- Configuration files use JSON format

## Future Migration Notes

### From Self-Hosted to Docker

```bash
# 1. Backup your configuration
cp -r ~/.config/amf ./amf-config-backup

# 2. Clone the repository
git clone https://github.com/amf/automated-manuscript-formatter.git

# 3. Copy your configuration
cp amf-config-backup/config.json automated-manuscript-formatter/backend/.env

# 4. Deploy with Docker
cd automated-manuscript-formatter
docker compose up -d
```
