<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: "ADR 002: Redis Realtime Backbone"
description: Decision to use Redis pub/sub as the realtime communication backbone
sidebar_position: 41
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 002: Redis Realtime Backbone

**Context:** The platform needs real-time streaming updates and low-latency pub/sub for SSE and WebSocket connections.

**Decision:** Use Redis as the realtime backbone for pub/sub, caching, and queue depth monitoring, with in-memory fallbacks when Redis is unavailable.

**Consequences:** Production environments must provision Redis for full realtime features. Monitoring includes Redis health and queue depth metrics.

**See also:** [ADR 006: Celery for Background Tasks](006-celery-background-tasks.md), [ADR 003: API Versioning Strategy](003-api-versioning-strategy.md)
