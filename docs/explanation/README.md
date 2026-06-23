<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Explanatory Documentation
description: Conceptual explanations of ScholarForm AI architecture and design decisions
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: June 2026
---

# Explanatory Documentation

Conceptual guides explaining how and why ScholarForm AI works the way it does.

| Document | Description |
|----------|-------------|
| [Why FastAPI Only](why-fastapi-only.md) | Architectural decision to use FastAPI as the sole backend gateway |
| [Pipeline Architecture](pipeline-architecture.md) | How the 12-stage formatting pipeline works end-to-end |
| [LLM Fallback Strategy](llm-fallback-strategy.md) | Multi-tier LLM provider failover design |
| [Security Model](security-model.md) | Defense-in-depth: from upload to delivery |

These documents explain the *reasoning* behind our design choices. For *how-to* instructions, see the [Guides](../guides/README.md). For *step-by-step* learning, see [Tutorials](../tutorials/README.md).
