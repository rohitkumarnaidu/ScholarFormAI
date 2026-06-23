<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 004: FastAPI as Sole API Gateway"
description: Decision to use FastAPI-only architecture without Spring Boot gateway
sidebar_position: 43
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: June 2026
---

# ADR 004: FastAPI as Sole API Gateway

**See also:** [ADR 003: API Versioning Strategy](003-api-versioning-strategy.md), [ADR 010: Next.js App Router](010-nextjs-app-router.md)

## Context

Earlier architecture documents referenced a Spring Boot gateway between the frontend and backend services. As the project evolved, no Spring Boot code was ever written, and FastAPI handles all routing directly.

## Decision

Remove all references to a Spring Boot gateway. FastAPI is the single entry point for all API requests. There is no secondary gateway layer.

## Consequences

- Simpler deployment (one service to manage instead of two)
- Reduced latency (no proxy hop)
- All rate limiting, auth, and CORS concerns handled in FastAPI middleware
- Documentation must not reference a Spring Boot tier
