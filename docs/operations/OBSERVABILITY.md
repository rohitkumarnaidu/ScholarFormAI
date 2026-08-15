# Observability

Observability in ScholarForm AI is designed to provide deep insights into the internal state of our microservices, particularly the complex multi-agent interactions during manuscript generation and formatting.

## Core Pillars

1. **Metrics**: Real-time numerical data (see [Monitoring](MONITORING.md)).
2. **Logging**: Centralized, structured logs.
3. **Tracing**: Distributed request tracing across components.

## Distributed Tracing (OpenTelemetry)

We utilize OpenTelemetry to instrument all services, propagating trace context via HTTP headers and Celery message headers.

- **Next.js**: Instruments API routes and server-side rendering.
- **FastAPI**: Uses the OpenTelemetry FastAPI instrumentation to trace incoming requests, database calls (SQLAlchemy), and Redis caching.
- **Celery**: Traces task enqueuing and execution.
- **AI Agents**: Custom spans trace the lifecycle of LLM calls, tracking prompt preparation, generation latency, and response parsing.

### Trace Visualization (Jaeger / Tempo)

Traces are exported to our backend tracing system (Jaeger or Grafana Tempo). This allows us to visualize bottlenecks, such as a long-running PyMuPDF extraction followed by an LLM synthesis step.

## Centralized Logging

All logs are output in JSON format to stdout/stderr and collected via Promtail/FluentBit, forwarding them to Loki or Elasticsearch.

- **Standard Fields**: `timestamp`, `level`, `service_name`, `trace_id`, `span_id`, `message`.
- **Backend Logs**: Provide detailed context on API requests and WebSocket event streams.
- **Celery Logs**: Tagged with `task_id` for easy correlation of background jobs.
- **Frontend Logs**: Client-side errors are captured and sent to a centralized logging endpoint.

## Cross-References

- [Monitoring Dashboards](MONITORING.md)
- [Deployment Configuration](DEPLOYMENT.md)
