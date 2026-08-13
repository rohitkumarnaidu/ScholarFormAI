# Migration Guide

This document outlines the steps necessary to migrate between major versions of ScholarFormAI APIs and SDKs.

## Migrating from v1 to v2

API v2 introduces a fundamentally different approach to asynchronous processing and introduces breaking changes to the payload structure.

### 1. Endpoint Changes
- **Format Endpoint:** 
  - `v1`: `POST /v1/format` (Synchronous by default)
  - `v2`: `POST /v2/jobs` (Strictly asynchronous)

### 2. Payload Structure
In v1, `template_id` was passed directly in the form data. In v2, options are strictly validated via JSON.

**v1 Request:**
```http
POST /v1/format
Content-Type: multipart/form-data
file=@my_file.docx
template_id=apa-7
```

**v2 Request:**
```http
POST /v2/jobs
Content-Type: multipart/form-data
file=@my_file.docx
metadata={"template": "apa-7"}
```

### 3. Handling Responses
In v2, all formatting requests return a `job_id`. You must implement a polling mechanism or register a webhook to retrieve the finished document.

### 4. SDK Updates
If using our SDKs, simply bump the version to `^2.0.0`. The SDKs abstract the polling mechanism, so `client.formatDocument()` behaves synchronously for the developer, handling the polling under the hood automatically.

See the [Upgrade Guide](UPGRADE_GUIDE.md) for specifics on updating your infrastructure.
