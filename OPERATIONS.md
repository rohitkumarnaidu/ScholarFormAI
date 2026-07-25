# Operations Guide

## System Requirements

### Minimum
- 2 CPU cores
- 2GB RAM
- 10GB disk space

### Recommended
- 4 CPU cores
- 4GB RAM
- 50GB SSD

## Monitoring

### Health Check

```bash
# API health
curl http://localhost:8000/health

# Expected response:
{"status": "healthy", "version": "1.0.0", "service": "Automated Manuscript Formatter", "uptime": 1234.56}
```

### Metrics to Monitor

- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (5xx responses)
- Concurrent formatting operations
- Disk usage (uploads directory)
- Memory usage

## Logging

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: Normal operational messages
- `WARNING`: Indications of potential issues
- `ERROR`: Error conditions that should be investigated
- `CRITICAL`: Severe conditions requiring immediate action

### Log Format

```
2026-07-25 10:30:00 | INFO     | app.api.routes:format_manuscript:42 | Formatted manuscript 'Title' with style 'apa' (15 pages)
```

## Backup

### What to Backup

- Configuration files
- Custom style definitions
- Uploaded manuscripts (optional)

### Backup Schedule

- Configuration: Daily
- Uploads: Weekly

## Upgrades

### Rolling Upgrade

1. Pull new images: `docker compose pull`
2. Recreate services: `docker compose up -d`
3. Verify health: `curl http://localhost:8000/health`

### Upgrade Checklist

- [ ] Review CHANGELOG for breaking changes
- [ ] Backup configuration
- [ ] Perform upgrade in staging first
- [ ] Run health checks
- [ ] Verify formatting quality with test manuscripts

## Troubleshooting

### High Memory Usage

1. Check `AMF_MAX_UPLOAD_SIZE` configuration
2. Consider adding memory limits to Docker
3. Scale horizontally instead of vertically

### Slow Response Times

1. Check concurrent formatting requests
2. Monitor CPU and memory
3. Consider load balancing

### Disk Full

1. Clean up temporary files: `cleanup` directory
2. Reduce upload TTL
3. Increase disk size
