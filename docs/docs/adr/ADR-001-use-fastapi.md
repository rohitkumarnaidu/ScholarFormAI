# ADR-001: Use FastAPI as the Backend Framework

- **Status:** Accepted
- **Date:** 2026-01-15
- **Author:** ScholarForm AI Engineering Team

## Context

ScholarForm AI requires a Python backend framework capable of handling AI pipeline orchestration with concurrent document processing. The framework must support:

- Async I/O for non-blocking LLM calls, PDF parsing, and database queries
- High throughput for concurrent document formatting jobs
- Strong typing to maintain code quality across 27+ services
- Automatic API documentation for internal and external consumers
- Pydantic integration for request/response validation on 39 API routes

The team evaluated four candidates: Django, Flask, Starlette, and FastAPI.

## Decision

We chose **FastAPI** over the alternatives.

| Criterion | FastAPI | Django | Flask | Starlette |
|-----------|---------|--------|-------|-----------|
| Native async | ✅ Built-in | ❌ Sync ORM | ❌ Extension | ✅ Built-in |
| Pydantic integration | ✅ First-class | ❌ Separate lib | ❌ Separate lib |  ️ Manual |
| OpenAPI auto-doc | ✅ Automatic | ❌ DRF needed | ❌ Extension | ❌ Manual |
| Performance | ⚡ ASGI-native | 🐌 WSGI | 🐌 WSGI | ⚡ ASGI-native |
| Opinionated structure |  ️ Minimal | ✅ Batteries-included |  ️ Minimal | ❌ Too minimal |

Django was ruled out due to its synchronous ORM and thread-per-request model, which conflicts with the async-heavy AI pipeline. Flask lacks native async and requires extensions for validation. Starlette is too low-level and would require building the validation layer from scratch. FastAPI provides the right balance of structure and flexibility.

## Consequences

**Positive:**
- Native `async def` endpoints enable concurrent LLM calls and database queries without thread pool overhead
- Pydantic models serve double duty: request validation + OpenAPI schema generation, eliminating drift between docs and implementation
- Automatic OpenAPI docs at `/docs` reduce onboarding time for new engineers
- Dependency injection system simplifies cross-cutting concerns (auth, rate limiting, DB sessions)
- ASGI compatibility allows future WebSocket support for real-time formatting progress

**Negative:**
- Smaller ecosystem than Django — some integrations (admin panels, CMS) require manual effort
- Async ORM (SQLAlchemy async) adds complexity compared to Django ORM
- Startup time is slower than Flask due to Pydantic model loading
- Less opinionated — teams must establish their own project conventions

## Compliance

This decision has been implemented and is verified by:
- `backend/tests/test_main.py` — FastAPI application creation and lifespan
- `backend/tests/test_routers_enterprise.py` — all 39 API routes served via FastAPI
- `backend/tests/test_openapi_docs.py` — OpenAPI schema generation
- `backend/tests/test_api_contracts.py` — Pydantic request/response validation
- `backend/app/main.py` — FastAPI app with 11 middleware layers
- `backend/pyproject.toml` — FastAPI + Uvicorn dependencies

## Cross-References

- [ADR 004: FastAPI as Sole API Gateway](004-fastapi-only-gateway.md) — supersedes the Spring Boot gateway reference
- [Why FastAPI Only](../explanation/why-fastapi-only.md) — detailed rationale
- [Architecture Overview](../architecture.md) — system layers and middleware stack
