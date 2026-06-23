<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 003: API Versioning Strategy"
description: Decision to use URL-based versioning with /v1/ prefix
sidebar_position: 42
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: June 2026
---

# ADR 003: API Versioning Strategy

**Context:** Clients depend on stable APIs while the backend evolves rapidly.

**Decision:** Maintain versioned APIs under `/api/v1` and keep legacy endpoints with deprecation notices.

**Consequences:** New features ship in `/api/v1` first. Legacy routes remain available until explicitly deprecated and removed.

**See also:** [ADR 004: FastAPI as Sole API Gateway](004-fastapi-only-gateway.md), [docs/API_VERSIONING.md](../API_VERSIONING.md)
