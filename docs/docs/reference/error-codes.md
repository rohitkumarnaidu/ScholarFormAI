# ScholarForm AI — Error Codes & Response Envelope Reference

ScholarForm AI standardizes all API error outputs using the `api_envelope` schema (`APIResponse`).

---

## Standard Error Response Format (`APIResponse`)

When an API error occurs, the server responds with an HTTP status code matching the error condition and a structured `APIResponse` error envelope:

```json
{
  "data": null,
  "error": {
    "code": "FMT_STYLE_NOT_FOUND",
    "message": "The requested formatting style 'ieee-custom' was not found.",
    "details": {
      "requested_style": "ieee-custom",
      "available_builtin": ["ieee", "apa", "mla", "chicago", "nature"]
    }
  },
  "request_id": "req-9b8a7c6d-4e5f",
  "timestamp": "2026-07-29T12:00:00Z"
}
```

---

## Error Code Taxonomy (Domain-Specific Prefixes)

ScholarForm AI categorizes machine-readable error codes using domain prefixes to simplify client debugging and error handling:

### 1. Authentication & Security (`AUTH_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `AUTH_FAILED` | 401 | Bearer token verification failed | Re-authenticate and obtain fresh JWT |
| `AUTH_TOKEN_EXPIRED` | 401 | JWT bearer token has expired | Request new access token via `/api/v1/auth/login` |
| `AUTH_INVALID_CREDENTIALS` | 401 | Incorrect email or password provided | Check user login credentials |
| `AUTH_MISSING_HEADER` | 401 | Required `Authorization` header missing | Include `Authorization: Bearer <token>` |

---

### 2. Document Operations (`DOC_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `DOC_NOT_FOUND` | 404 | Target document or job ID not found | Verify job ID or document UUID |
| `DOC_INVALID_FORMAT` | 400 | File format not supported | Upload supported file type (`.docx`, `.pdf`, `.md`, `.txt`) |
| `DOC_EXCEEDS_SIZE_LIMIT` | 413 | Upload file exceeds 60MB limit | Compress images or split document |
| `DOC_PARSING_FAILED` | 422 | GROBID or PyMuPDF failed to extract text | Ensure file is not corrupted or password-protected |

---

### 3. Formatter Engine (`FMT_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `FMT_STYLE_NOT_FOUND` | 404 | Requested citation or template style not found | Check `/api/v1/templates` for valid style IDs |
| `FMT_ENGINE_ERROR` | 500 | `python-docx` or layout rendering engine error | Report issue with sample document |
| `FMT_RULE_VIOLATION` | 422 | Manuscript structure violates target style rules | Review validation report error details |
| `FMT_EXPORT_FAILED` | 500 | Pandoc or LibreOffice PDF export failure | Ensure LibreOffice / Pandoc binaries installed |

---

### 4. AI Generator Session (`GEN_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `GEN_SESSION_NOT_FOUND` | 404 | Generator session ID does not exist | Create new session via `/api/v1/generator/sessions` |
| `GEN_STREAM_TIMEOUT` | 504 | SSE drafting stream timed out | Check downstream LLM provider status |
| `GEN_PROMPT_INVALID` | 400 | Prompt input is empty or invalid | Provide non-empty topic description |
| `GEN_OUTLINE_REJECTED` | 400 | Attempted generation without approving outline | Approve outline via `/outline/approve` first |

---

### 5. RAG & Intelligence Engine (`RAG_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `RAG_EMBEDDING_FAILED` | 503 | Sentence-transformers or embedding model error | Check `RAG_USE_TRANSFORMERS` setting |
| `RAG_CONTEXT_EMPTY` | 422 | No relevant context found in vector store | Upload reference documents or broaden query |
| `RAG_VECTOR_STORE_ERROR` | 500 | ChromaDB vector store read/write failure | Restart backend vector store service |

---

### 6. Rate Limiting (`RATE_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `RATE_LIMIT_EXCEEDED` | 429 | IP or key exceeded requests per minute limit | Wait for `Retry-After` seconds before retrying |
| `RATE_QUOTA_EXHAUSTED` | 429 | Monthly tier upload quota exhausted | Upgrade subscription plan via `/api/v1/billing` |

---

### 7. Citation & CSL Engine (`CITE_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `CITE_CSL_FETCH_FAILED` | 503 | Failed to download CSL XML from repository | Check network connection or CSL style ID |
| `CITE_CROSSREF_UNAVAILABLE` | 503 | CrossRef API lookup endpoint timed out | Set `CROSSREF_MAILTO` or retry later |
| `CITE_PARSING_ERROR` | 422 | Malformed bib entry or DOI resolution failed | Validate reference DOI syntax |

---

### 8. System & Infrastructure (`SYS_*`)

| Error Code | HTTP Status | Description | Troubleshooting Action |
| --- | --- | --- | --- |
| `SYS_INTERNAL_ERROR` | 500 | Unhandled internal backend exception | Inspect server error log / correlation request ID |
| `SYS_SERVICE_UNAVAILABLE` | 503 | Database or Redis cache unavailable | Check backend service health (`/api/v1/health`) |
| `SYS_MAINTENANCE_MODE` | 503 | System is down for scheduled maintenance | Retry request after maintenance window |

---

## Standard System HTTP Status Mappings

| Error Code (`code`) | HTTP Status | System Description |
| --- | --- | --- |
| `BAD_REQUEST` | 400 | Malformed client request syntax or invalid parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication bearer token |
| `FORBIDDEN` | 403 | Authenticated user lacks permission for operation |
| `NOT_FOUND` | 404 | Target resource, document, or template ID not found |
| `CONFLICT` | 409 | Resource state conflict (e.g. concurrent updates) |
| `PAYLOAD_TOO_LARGE` | 413 | Manuscript file upload size exceeds max limit (60MB) |
| `VALIDATION_ERROR` | 422 | Manuscript structure validation failed |
| `RATE_LIMITED` | 429 | Rate limit request quota exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled internal server execution error |
| `NOT_IMPLEMENTED` | 501 | Endpoint or feature is not yet supported |
| `BAD_GATEWAY` | 502 | Upstream proxy or service gateway failure |
| `SERVICE_UNAVAILABLE` | 503 | Downstream AI provider or database connection error |

---

## Manuscript Validation Issue Codes (`ValidationIssue`)

Structural validation issue codes returned in manuscript analysis reports:

| Issue Code | Default Severity | Description |
| --- | --- | --- |
| `MISSING_TITLE` | `error` | No manuscript title detected in input document |
| `SHORT_TITLE` | `warning` | Title length is below recommended guidelines |
| `LONG_TITLE` | `warning` | Title length exceeds style guidelines |
| `MISSING_AUTHORS` | `error` | At least one author is required |
| `INCOMPLETE_AUTHOR` | `warning` | Author entry missing affiliation or email |
| `MISSING_ABSTRACT` | `error` | Abstract required by selected journal style |
| `LONG_ABSTRACT` | `warning` | Abstract exceeds word count limit |
| `MISSING_KEYWORDS` | `warning` | Keywords recommended for journal indexing |
| `TOO_MANY_KEYWORDS` | `warning` | Keyword count exceeds target threshold |
| `MISSING_SECTIONS` | `warning` | Document lacks section headings |
| `EMPTY_SECTION` | `error` | Section heading exists without content body |
| `NO_REFERENCES` | `warning` | Bibliography reference list is empty |
| `MISSING_REFERENCE_TITLE` | `error` | Reference entry missing title field |
| `INCOMPLETE_REFERENCE` | `warning` | Reference missing journal, year, or page info |
| `LONG_ACKNOWLEDGMENTS` | `warning` | Acknowledgments section exceeds length limits |

---

## SDK & CLI Exception Mappings

### 1. Python SDK Mapping (`amf_sdk.exceptions`)

| HTTP Status Code | SDK Exception Class | Extra Properties |
| --- | --- | --- |
| `400` | `AMFValidationError` | `details: Dict[str, Any]` |
| `401` | `AMFAuthenticationError` | None |
| `404` | `AMFNotFoundError` | `resource: str` |
| `422` | `AMFFormattingError` | `details: Dict[str, Any]` |
| `429` | `AMFRateLimitError` | `details["retry_after"]` (seconds) |
| `503` | `AMFConnectionError` | Default message: `"Failed to connect to AMF API"` |
| `504` | `AMFTimeoutError` | Default message: `"Request timed out"` |
| Any unmapped 5xx | `AMFError` | Base exception with `status_code` |

---

### 2. CLI Exit Codes

| Exit Code | Meaning | Typical Cause |
| --- | --- | --- |
| `0` | Success | Command completed successfully |
| `1` | Runtime Error | File not found, REST API connection error without local fallback |
| `2` | Validation Failure | Manuscript failed validation rule checks or invalid CLI argument |

---

## Troubleshooting Guide

### 1. Troubleshooting API Consumers

1. **Inspect Envelope `request_id`:** Always record `request_id` when reporting API errors.
2. **Check HTTP 401 Errors:** Ensure your Bearer token is valid and not expired. Verify token header format (`Authorization: Bearer <token>`).
3. **Handle HTTP 429 Rate Limits:** Read the `Retry-After` HTTP header or `details["retry_after"]` payload field before resending requests.
4. **Fix HTTP 422 Validation Errors:** Check `error.details` for specific field paths (`missing_fields`) that failed validation.

### 2. Troubleshooting CLI Users

1. **Verbose Debug Mode:** Add `-v` / `--verbose` flag to any CLI command (`amf -v format -i paper.md -s apa`).
2. **API Offline Fallback:** If the API server is down, install `pip install amf-cli[local]` to enable local Python formatting without server connectivity.
3. **Config File Inspection:** Run `amf config` to verify the configured `api_endpoint` URL.

### 3. Troubleshooting SDK Developers

1. **Catch Specific Exceptions:** Always handle `AMFValidationError` and `AMFRateLimitError` explicitly before catching `AMFError`.
2. **Timeout Adjustments:** For large manuscripts (>100 pages), increase `timeout` parameter when initializing `AMFClient(timeout=60.0)`.
3. **Async Event Loops:** Ensure `AsyncAMFClient` is called inside an active `asyncio` event loop using `async with AsyncAMFClient(...)`.
