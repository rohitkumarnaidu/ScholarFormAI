# Error Codes

## API Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `MISSING_TITLE` | 400 | No title in manuscript |
| `MISSING_AUTHORS` | 400 | No authors specified |
| `MISSING_ABSTRACT` | 400 | Abstract required for style |
| `MISSING_REFERENCE_TITLE` | 400 | Reference missing title |
| `STYLE_NOT_FOUND` | 404 | Style ID not registered |
| `FORMATTING_ERROR` | 422 | Formatting engine failure |
| `UNSUPPORTED_FORMAT` | 400 | Input format unsupported |
| `MANUSCRIPT_TOO_LARGE` | 413 | File exceeds size limit |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

## CLI Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation failed |

## Validation Issue Codes

| Code | Severity | Description |
|------|----------|-------------|
| `MISSING_TITLE` | error | Required title missing |
| `SHORT_TITLE` | warning | Title too short |
| `LONG_TITLE` | warning | Title too long |
| `INCOMPLETE_AUTHOR` | warning | Author missing name parts |
| `LONG_ABSTRACT` | warning | Abstract too long |
| `MISSING_KEYWORDS` | warning | Keywords recommended |
| `TOO_MANY_KEYWORDS` | warning | Too many keywords (>10) |
| `MISSING_SECTIONS` | warning | No sections found |
| `EMPTY_SECTION` | error | Section without heading |
| `NO_REFERENCES` | warning | No references included |
| `INCOMPLETE_REFERENCE` | warning | Reference missing DOI/URL |
| `LONG_ACKNOWLEDGMENTS` | warning | Acknowledgments too long |

## SDK Exceptions

| Exception | Status | Cause |
|-----------|--------|-------|
| `AMFValidationError` | 400 | Invalid input |
| `AMFAuthenticationError` | 401 | Bad API key |
| `AMFNotFoundError` | 404 | Resource missing |
| `AMFFormattingError` | 422 | Format failure |
| `AMFRateLimitError` | 429 | Rate limit hit |
| `AMFConnectionError` | 503 | Cannot connect |
| `AMFTimeoutError` | 504 | Request timed out |
