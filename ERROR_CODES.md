# Error Codes Reference

## API Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `MISSING_TITLE` | 400 | Manuscript title is required |
| `MISSING_AUTHORS` | 400 | At least one author required |
| `MISSING_ABSTRACT` | 400 | Abstract required for style |
| `MISSING_REFERENCE_TITLE` | 400 | Reference missing title |
| `STYLE_NOT_FOUND` | 404 | Style ID not found |
| `FORMATTING_ERROR` | 422 | Formatting engine error |
| `UNSUPPORTED_FORMAT` | 400 | Input format not supported |
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
| `MISSING_TITLE` | error | No title found |
| `SHORT_TITLE` | warning | Title too short |
| `LONG_TITLE` | warning | Title too long |
| `MISSING_AUTHORS` | error | No authors |
| `INCOMPLETE_AUTHOR` | warning | Author missing name parts |
| `MISSING_ABSTRACT` | error | Abstract required but missing |
| `LONG_ABSTRACT` | warning | Abstract too long |
| `MISSING_KEYWORDS` | warning | Keywords recommended |
| `TOO_MANY_KEYWORDS` | warning | Too many keywords |
| `MISSING_SECTIONS` | warning | No sections found |
| `EMPTY_SECTION` | error | Section without heading |
| `NO_REFERENCES` | warning | No references |
| `MISSING_REFERENCE_TITLE` | error | Reference missing title |
| `INCOMPLETE_REFERENCE` | warning | Reference missing details |
| `LONG_ACKNOWLEDGMENTS` | warning | Acknowledgments too long |

## SDK Error Classes

| Exception | HTTP Status | When Raised |
|-----------|-------------|-------------|
| `AMFValidationError` | 400 | Invalid input |
| `AMFAuthenticationError` | 401 | Invalid API key |
| `AMFNotFoundError` | 404 | Resource not found |
| `AMFFormattingError` | 422 | Formatting failed |
| `AMFRateLimitError` | 429 | Rate limit hit |
| `AMFConnectionError` | 503 | Connection failed |
| `AMFTimeoutError` | 504 | Request timed out |
