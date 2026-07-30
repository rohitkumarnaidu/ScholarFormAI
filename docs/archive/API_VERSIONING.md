<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — API Versioning Strategy
description: Versioning policy, migration plan, and deprecation timeline
sidebar_position: 7
version: "1.0"
status: ✅ Complete
owner: Engineering Team
review_cadence: quarterly
last_updated: July 2026
---

# ScholarForm AI — API Versioning Strategy

**Current Version:** v1  
**Next Version:** v2 (planned)

> **See also:** [API Reference](API.md), [ADR 003: API Versioning Strategy](adr/003-api-versioning-strategy.md)

---

## Versioning Policy

ScholarForm AI uses **URL-based versioning** for API endpoints:

- Current: `/api/v1/...`
- Next: `/api/v2/...` (when released)

### Version Lifecycle

| Phase | Duration | Description |
| ------- | ---------- | ------------- |
| **Current** | Active | Fully supported, receives all updates |
| **Maintenance** | 6 months | Bug fixes only, no new features |
| **Deprecated** | 3 months | Returns `Deprecation` header, docs marked |
| **Sunset** | 0 | Returns 410 Gone, redirects to migration guide |

### Deprecation Headers

```
Deprecation: true
Sunset: Sat, 01 Jan 2028 00:00:00 GMT
Link: <https://scholarform.onrender.com/api/v2-migration>; rel="successor-version"
```

---

## v1 → v2 Migration Plan (Future)

### Breaking Changes Expected

1. **Response envelope** — Standardize on `{ data, error, meta }` format
2. **Pagination** — Cursor-based instead of offset-based
3. **Authentication** — API key header instead of Bearer token for programmatic access
4. **Webhook format** — Standardized event schema with signatures

### Non-Breaking Changes

1. New endpoints added to v2 only
2. New optional fields in responses
3. Additional query parameters

### Migration Timeline (When v2 is ready)

| Date | Milestone |
| ------ | ----------- |
| T-6 months | v2 beta released, docs published |
| T-3 months | v1 enters maintenance mode |
| T-0 | v2 GA, v1 deprecated |
| T+3 months | v1 sunset, 410 responses |

---

## Current API Version: v1

### Endpoints

| Category | Path | Status |
| ---------- | ------ | -------- |
| Health | `/api/v1/health/*` | ✅ Active |
| Documents | `/api/v1/documents/*` | ✅ Active |
| Templates | `/api/v1/templates/*` | ✅ Active |
| Generator | `/api/v1/generator/*` | ✅ Active |
| API Keys | `/api/v1/keys/*` | ✅ Active |
| Feedback | `/api/v1/feedback/*` | ✅ Active |

### API Version Detection

```python
# Middleware checks for version header or URL path
@app.middleware("http")
async def api_version_check(request: Request, call_next):
    version = request.headers.get("X-API-Version", "v1")
    if version not in ("v1",):
        return JSONResponse(
            status_code=400,
            content={"error": f"Unsupported API version: {version}"}
        )
    return await call_next(request)
```
