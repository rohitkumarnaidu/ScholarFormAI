# System Design

## Design Principles

1. **Separation of Concerns**: Parser, validator, formatter, and API are independent modules.
2. **Extensibility**: New styles, parsers, and output formats can be added without modifying core code.
3. **API-First**: All functionality is available via the REST API. UI and CLI are API consumers.
4. **Defensive Design**: All inputs are validated. Graceful error handling at every layer.

## API Design

### Endpoint Conventions

- Base path: `/api/v1/`
- Consistent error format: `{ "error": "CODE", "message": "...", "details": {} }`
- Request IDs on all responses via `X-Request-ID` header

### Rate Limiting

- `/api/v1/format`: 10 requests/minute per IP (configurable)
- `/api/v1/validate`: 30 requests/minute per IP
- `/api/v1/preview`: 20 requests/minute per IP

## Database Schema (Future)

While v1 is stateless, future versions may require:

```
users
├── id (UUID, PK)
├── email (unique)
├── projects
│   ├── id (UUID, PK)
│   ├── user_id (FK)
│   ├── title
│   ├── style_id
│   ├── created_at
│   └── versions
│       ├── id (UUID, PK)
│       ├── project_id (FK)
│       ├── content (JSON)
│       ├── formatted_docx_path
│       └── created_at
```

## Security Model

### Authentication

- Optional API key authentication
- API keys passed via `Authorization: Bearer <key>` header
- Keys configurable via environment variables

### Input Validation

- Manuscript text: Max 10MB
- File uploads: Validated for type (.md, .tex, .txt)
- API payloads: Validated by Pydantic schemas

### Output Security

- Generated DOCX files scanned for macros (none are generated)
- HTML preview sanitized
- Temporary files cleaned up after configurable TTL

## Error Handling

All errors follow a standard format:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Manuscript title is required",
  "details": {
    "field": "title",
    "code": "MISSING_TITLE"
  }
}
```

## Logging

- Structured JSON logging (future)
- Request-level logging with request IDs
- Log levels: DEBUG (dev), INFO (prod)
- Sensitive data redacted from logs

## Monitoring

- Health check endpoint: `GET /health`
- Request timing via `X-Request-Time` header
- Prometheus metrics (future)
- Sentry integration (future)
