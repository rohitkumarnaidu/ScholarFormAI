<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: Why FastAPI Only
description: Explaining the decision to use FastAPI as the sole backend gateway
sidebar_position: 2
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# Why FastAPI Only

## Context

Early planning documents for ScholarForm AI (including the initial PRD) specified a **Spring Boot API Gateway** as a separate service sitting between the Next.js frontend and the Python backend. The gateway was intended to handle authentication, rate limiting, and request routing.

## Decision

We chose to **eliminate the Spring Boot gateway entirely** and handle all gateway responsibilities within FastAPI middleware.

## Rationale

### 1. Simplicity

A separate gateway adds deployment complexity, a second language/runtime to maintain, and an additional network hop. FastAPI's middleware stack handles everything the gateway would have done:

- JWT verification → `jwks_verifier.py` middleware
- Rate limiting → `rate_limit.py` + `tier_rate_limit.py` middleware
- Request correlation → `request_id.py` middleware
- Security headers → `security_headers.py` middleware
- CORS → FastAPI built-in `CORSMiddleware`

### 2. Performance

Each network hop adds 1-5ms latency. For a live preview endpoint targeting <80ms render time, every millisecond matters. Removing the gateway saves 2-10ms per request.

### 3. Operational Cost

A Spring Boot gateway would require:

- A JVM runtime (additional ~200MB RAM)
- A separate Render web service or container
- Additional CI pipeline to build and deploy
- Cross-team knowledge (Java + Python)

FastAPI middleware is Python — the same language as the rest of the backend.

### 4. Single Responsibility

The Spring Boot gateway was originally proposed to handle "enterprise concerns" like auth and routing. But FastAPI's middleware system handles these equally well, and keeping them in-process means they have access to the same application state (database pools, Redis connections, Prometheus metrics).

## Consequences

- All 34 API routes are defined directly in FastAPI routers under `backend/app/routers/`
- Middleware execution order is explicit and configurable (see [Architecture](../architecture.md#middleware-stack-execution-order))
- Future API gateway concerns (like API composition or BFF patterns) will be handled via FastAPI middleware or sub-applications, not a separate service
- Early PRD references to "Spring Boot API Gateway" are obsolete — see [ADR 004](../adr/004-fastapi-only-gateway.md)

## See Also

- [ADR 004: FastAPI as Sole API Gateway](../adr/004-fastapi-only-gateway.md) — formal architecture decision record
- [Architecture Overview](../architecture.md) — system layers and middleware stack
- [Security Model](security-model.md) — full security architecture
