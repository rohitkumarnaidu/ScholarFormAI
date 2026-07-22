<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: "ADR 001: Python-First Runtime"
description: Decision to use Python as the primary backend runtime
sidebar_position: 40
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 001: Python-First Runtime

**Context:** ScholarForm AI relies on Python-first ML and document-processing libraries, and the existing backend codebase is fully Python.

**Decision:** Standardize on Python 3.12 for backend runtime and CI.

**Consequences:** Backend tooling, dependencies, and CI workflows are aligned to Python 3.12. Non-Python services are integrated via APIs rather than replatforming.

**See also:** [ADR 007: Render Deployment Platform](007-render-deployment-platform.md)
