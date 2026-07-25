# Observability

## Current Capabilities

### Request Tracing

- Each request gets a unique `X-Request-ID` header
- Response time tracked via `X-Request-Time` header
- Structured logging with request context

### Health Monitoring

- `GET /health` endpoint with status and uptime
- Docker health checks on all services
- Startup and shutdown event logging

### Logging

- Configurable log levels via `AMF_LOG_LEVEL`
- Request/response logging with timing
- Error logging with stack traces
- Log format includes timestamp, level, module, line number

## Planned Capabilities

### OpenTelemetry Integration (Q4 2026)

- Distributed tracing across services
- Metrics export to Prometheus
- Logs correlation with traces

### Dashboard (Q1 2027)

- Real-time formatting metrics
- Error rate monitoring
- Usage analytics
- System resource monitoring

### Structured Logging (Q4 2026)

- JSON log output format
- Log aggregation support (ELK, Loki)
- Log levels per service

## Configuration

```bash
# Set log level
AMF_LOG_LEVEL=debug   # Most verbose
AMF_LOG_LEVEL=info    # Default
AMF_LOG_LEVEL=warning # Quiet
AMF_LOG_LEVEL=error   # Errors only
```
