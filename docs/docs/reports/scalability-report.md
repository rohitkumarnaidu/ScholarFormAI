# Scalability Architecture Report — ScholarFormAI

**Document Version:** 1.0.0  
**Date:** 2026-07-29  
**Scope:** Horizontal Scaling, Asynchronous Queues, Vector Lifecycle Management, DB Pooling, Multi-Region Deployment  
**Classification:** Enterprise Scalability Architecture Audit  

---

## Executive Summary

This formal scalability report documents the architectural capabilities of ScholarFormAI regarding horizontal web tier expansion, asynchronous queue handling, automated vector store lifecycle management, cloud database connection pooling, and multi-region deployment readiness.

---

## 1. Observation

Core codebase audit highlights the following scalability mechanisms:

### Stateless Web Worker Tier
- **JWT-Based Authentication**: `backend/app/main.py` and API routers rely on stateless JWT token validation (`backend/app/middleware/auth.py`). No session state is retained in local worker memory.
- **Shared State Layer**: All operational state resides in external Supabase PostgreSQL databases and Redis instances.
- **Horizontal Scaling Verification**: Web workers support arbitrary container replica expansion via `docker compose up -d --scale backend=N`.

### Asynchronous Queue Architecture & Processing
- **Celery Dual-Queue Setup (`backend/app/tasks/celery_tasks.py`, lines 30-37)**:
  - **`interactive` Queue**: Low-latency tasks (preview generation, style checks).
  - **`batch` Queue**: Resource-heavy background operations (large document transformations, multi-document synthesis).
- **Asynchronous Task Definitions**: Includes `process_document_async`, `process_generation_async`, `process_synthesis_async`, `process_agent_pipeline_async`, and `process_edit_document_async`.
- **In-Process Pipeline Throttling**: Concurrency within individual worker nodes is bounded using `_MAX_CONCURRENT_JOBS = 5` semaphore (`backend/app/pipeline/orchestrator.py`).

### Vector Store Lifecycle & Purging
- **Session-Scoped Vector Tracking**: `backend/app/services/session_vector_store.py` tracks active session collections in Redis with configurable TTL (`vector_session:{session_id}:ttl`, default 24 hours).
- **Automated Celery Beat Cleanup**: Celery scheduled task `purge_expired_vector_sessions` (`backend/app/tasks/celery_tasks.py`, lines 266-316) runs hourly, checking ChromaDB collections against active Redis TTL keys and purging expired vector indices from disk.

### Database Connection Pooling & Degraded Operations
- **SQLAlchemy Connection Tuning (`backend/app/db/session.py`, lines 48-60)**:
  - `pool_size`: 5 base connections per worker process.
  - `max_overflow`: 10 temporary burst connections (up to 15 concurrent DB connections per worker).
  - `pool_timeout`: 30 seconds wait timeout.
  - `pool_recycle`: 1,800 seconds (30 minutes) connection recycling to prevent stale SSL sockets.
  - `pool_pre_ping`: True (verifies connection viability before query execution).
- **Graceful Startup Degraded Mode**: If `SUPABASE_DB_URL` is omitted, `_create_engine_safe()` returns `None`. The FastAPI server initializes successfully without crashing, and DB endpoints return HTTP 503 Service Unavailable.
- **Transient Fault Resilience**: Supabase REST interactions employ `_run_with_retry()` with exponential backoff across 3 retries.

### Multi-Region Infrastructure Readiness
- **Stateless Application Layer**: Decoupled backend workers enable deployment across geographically distributed container regions (e.g. AWS ECS, GCP Cloud Run, Render).
- **Pub/Sub Event Propagation**: Distributed real-time client notifications are synchronized across web nodes using `RedisPubSub` (`backend/app/realtime/pubsub.py`).

---

## 2. Logic Chain

The platform scalability architecture is established on strict technical principles:

1. **Stateless Web Nodes → Linear Horizontal Scalability**: By eliminating local session affinity, inbound traffic can be distributed across any number of backend replicas without session loss.
2. **Asynchronous Offloading → API Responsiveness Under Heavy Load**: Offloading heavy conversion and synthesis workloads to Celery workers isolates HTTP request threads, maintaining fast UI response times during peak background processing.
3. **Automated Vector Expiration → Bounded Storage Growth**: Ephemeral RAG embeddings generated during document sessions will exhaust local disk capacity over time if unmanaged. Linking ChromaDB collections to Redis TTLs and executing automated hourly purges ensures predictable storage consumption.

---

## 3. Caveats

- **Local Storage Scope of Default Vector Store**: In multi-worker environments without shared volumes (EFS/NFS), ChromaDB directories default to local worker storage; multi-worker access to the same session vector index requires centralized vector store deployment or shared volume mounts.
- **Database Connection Limits**: Total database pool size expands linearly with worker replica count; Supabase database connection limits must be configured to accommodate max total connections (`worker_count * 15`).

---

## 4. Conclusion

ScholarFormAI implements a scalable enterprise architecture. The platform supports horizontal worker expansion, resilient background queue processing, automated vector lifecycle management, and robust cloud database connection pooling.

---

## 5. Verification Method

To verify scalability configurations:

- **Celery Worker Task Registration**:
  ```bash
  celery -A app.tasks.celery_tasks inspect registered
  ```
  *Expected Output:* Confirms registration of `interactive` and `batch` tasks alongside `purge_expired_vector_sessions`.
- **Database Pool Configuration Check**:
  Inspect `backend/app/db/session.py` to confirm `pool_size=5` and `max_overflow=10`.
- **Continuous Integration Vector Purge Verification (CI Pipeline Only)**:
  ```bash
  pytest backend/tests/test_celery_tasks.py
  ```
