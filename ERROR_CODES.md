# Error Codes & Response Envelope Reference

ScholarForm AI standardizes all error responses using the `api_envelope` schema (`APIResponse`).

---

## Standard Error Envelope Schema

When an API error occurs, the server responds with an HTTP status code matching the error condition and an `APIResponse` error envelope:

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Manuscript validation failed: missing section headings.",
    "details": {
      "missing_fields": ["sections[0].heading"]
    }
  },
  "request_id": "req-9b8a7c6d-4e5f",
  "timestamp": "2026-07-28T21:00:00Z"
}
```

---

## System Error Codes (`backend/app/common/constants.py`)

The machine-readable stable error codes and their associated HTTP status codes:

| Error Code (`code`) | HTTP Status Code | Description |
|---|---|---|
| `BAD_REQUEST` | 400 | Malformed client request syntax or invalid parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication bearer token |
| `FORBIDDEN` | 403 | Authenticated user lacks necessary permissions |
| `NOT_FOUND` | 404 | Target resource, document, or template ID not found |
| `CONFLICT` | 409 | Resource state conflict (e.g., concurrent modifications) |
| `PAYLOAD_TOO_LARGE` | 413 | Manuscript or upload file exceeds size threshold (60MB max) |
| `VALIDATION_ERROR` | 422 | Manuscript structure or Pydantic validation failure |
| `RATE_LIMITED` | 429 | Rate limit request quota exceeded |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled internal server execution error |
| `NOT_IMPLEMENTED` | 501 | Endpoint or feature is not yet supported |
| `BAD_GATEWAY` | 502 | Upstream proxy or service integration gateway failure |
| `SERVICE_UNAVAILABLE` | 503 | Downstream AI provider or database connectivity error |

---

## Validation Issue Codes (`ValidationIssue`)

Specific issue codes returned inside manuscript structure validation reports:

| Issue Code | Default Severity | Description |
|---|---|---|
| `MISSING_TITLE` | `error` | No manuscript title detected |
| `SHORT_TITLE` | `warning` | Title length is below recommended threshold |
| `LONG_TITLE` | `warning` | Title length exceeds style limits |
| `MISSING_AUTHORS` | `error` | At least one author is required |
| `INCOMPLETE_AUTHOR` | `warning` | Author missing affiliation or contact details |
| `MISSING_ABSTRACT` | `error` | Abstract required by selected journal style |
| `LONG_ABSTRACT` | `warning` | Abstract exceeds word count limit |
| `MISSING_KEYWORDS` | `warning` | Keywords recommended for publication |
| `TOO_MANY_KEYWORDS` | `warning` | Keyword count exceeds target threshold |
| `MISSING_SECTIONS` | `warning` | Document lacks section headings |
| `EMPTY_SECTION` | `error` | Section heading exists without content body |
| `NO_REFERENCES` | `warning` | Bibliography list is empty |
| `MISSING_REFERENCE_TITLE` | `error` | Reference entry missing title field |
| `INCOMPLETE_REFERENCE` | `warning` | Reference missing journal, year, or page info |
| `LONG_ACKNOWLEDGMENTS` | `warning` | Acknowledgments section exceeds length limits |

---

## SDK Exception Mapping (`amf_sdk.exceptions`)

The Python SDK automatically maps HTTP response status codes to specific exception types:

| Exception Class | HTTP Status | Mapped Error Condition |
|---|---|---|
| `AMFValidationError` | 400 | Invalid payload / `BAD_REQUEST` |
| `AMFAuthenticationError` | 401 | Invalid token / `UNAUTHORIZED` |
| `AMFNotFoundError` | 404 | Missing resource / `NOT_FOUND` |
| `AMFFormattingError` | 422 | Processing failure / `VALIDATION_ERROR` |
| `AMFRateLimitError` | 429 | Rate limit exceeded / `RATE_LIMITED` |
| `AMFConnectionError` | 503 | Network failure / `SERVICE_UNAVAILABLE` |
| `AMFTimeoutError` | 504 | Gateway timeout / `TIMEOUT` |

---

## CLI Exit Codes

| Exit Code | Meaning |
|---|---|
| `0` | Successful execution |
| `1` | Command execution failure or uncaught exception |
| `2` | Manuscript validation or lint check failure |
