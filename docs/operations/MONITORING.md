# Monitoring Guide

## Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Automated Manuscript Formatter",
  "uptime": 3600.5
}
```

## Key Metrics

| Metric | Source | Description |
|--------|--------|-------------|
| Request rate | API middleware | Requests per second |
| Response time | API middleware | p50/p95/p99 latency |
| Error rate | API middleware | 4xx/5xx percentage |
| Active formats | Application | Concurrent formatting operations |
| Memory usage | System | RSS memory in MB |
| CPU usage | System | CPU utilization percentage |
| Disk usage | System | Upload directory usage |

## Prometheus (Future)

Planned metrics endpoint at `/metrics`:

```
# HELP amf_format_requests_total Total format requests
# TYPE amf_format_requests_total counter
amf_format_requests_total{style="apa"} 150

# HELP amf_format_duration_seconds Format duration
# TYPE amf_format_duration_seconds histogram
amf_format_duration_seconds_bucket{le="1"} 100
amf_format_duration_seconds_bucket{le="5"} 45
amf_format_duration_seconds_bucket{le="+Inf"} 5
```

## Logging

### Structured Logging (Future)

Logs will be output in JSON format for integration with log aggregation tools:

```json
{
  "timestamp": "2026-07-25T10:30:00Z",
  "level": "INFO",
  "service": "amf-backend",
  "request_id": "abc-123",
  "endpoint": "/api/v1/format",
  "duration_ms": 2100,
  "style": "apa",
  "pages": 15
}
```

## Alerts

### Critical
- Service unreachable
- Error rate > 5%
- Response time > 10s for p95

### Warning
- Response time > 3s for p95
- Error rate > 1%
- Disk usage > 80%

### Info
- Unusual request patterns
- Rate limit thresholds approached
