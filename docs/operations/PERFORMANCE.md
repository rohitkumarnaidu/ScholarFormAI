# Performance Tuning

ScholarForm AI must handle compute-intensive tasks, such as multi-page PDF parsing and extensive LLM generation. This document outlines our strategies for maintaining high performance and low latency.

## Frontend (Next.js)

- **Static Generation & Caching**: We heavily leverage the Next.js App Router caching mechanisms for static assets and unchanged views.
- **WebSockets / SSE**: The real-time split-pane editor uses WebSockets for live diffs and Server-Sent Events (SSE) for streaming LLM generation, ensuring low perceived latency.
- **Bundle Optimization**: Tree-shaking and dynamic imports minimize the initial JavaScript payload.

## Backend (FastAPI)

- **Asynchronous I/O**: All database queries (via `asyncpg` and SQLAlchemy async), Redis calls, and external API requests (Groq/NVIDIA) must be non-blocking.
- **Uvicorn Workers**: In production, Uvicorn is run with Gunicorn using `uvicorn.workers.UvicornWorker`. Rule of thumb: `(2 x $num_cores) + 1` workers.
- **Database Connection Pooling**: SQLAlchemy is configured with a robust connection pool size and overflow limit matching the Uvicorn worker count.

## Asynchronous Processing (Celery)

Formatting and generation are offloaded to Celery.

- **Concurrency**: Adjust the Celery concurrency based on whether the tasks are CPU-bound (PDF extraction) or I/O-bound (LLM API calls). Use `gevent` or `eventlet` pools for heavy I/O workloads.
- **Task Batching & Routing**: Dedicated queues for "fast" (e.g., Markdown formatting) and "slow" (e.g., PDF generation) tasks prevent head-of-line blocking.

## Caching Strategy (Redis)

- **LLM Responses**: Repetitive queries or common template structures are cached.
- **Rate Limiting**: Redis is used for high-performance, distributed rate limiting to protect our API and external LLM quota.

## Cross-References

- [Benchmarks](BENCHMARKS.md)
- [Configuration Guide](CONFIGURATION.md)
