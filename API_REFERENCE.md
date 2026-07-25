# API Reference

## Base URL

- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

All endpoints are prefixed with `/api/v1`.

## Authentication

Optional. Pass API key via header:

```
Authorization: Bearer your-api-key
```

## Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Automated Manuscript Formatter",
  "uptime": 1234.56
}
```

### Format Manuscript

```
POST /api/v1/format
```

Request body:
```json
{
  "manuscript": {
    "title": "The Impact of AI on Research",
    "authors": [
      {
        "first_name": "Jane",
        "last_name": "Smith",
        "affiliation": "University of Research",
        "email": "jane@research.edu"
      }
    ],
    "abstract": "This study examines...",
    "keywords": ["AI", "research"],
    "sections": [
      {
        "heading": "Introduction",
        "level": 1,
        "content": [
          {
            "text": "This is the introduction paragraph.",
            "style": "normal"
          }
        ],
        "subsections": []
      }
    ],
    "references": [
      {
        "authors": [{"first_name": "Alan", "last_name": "Turing"}],
        "year": "1950",
        "title": "Computing Machinery and Intelligence",
        "journal": "Mind",
        "volume": "59",
        "issue": "236",
        "pages": "433-460"
      }
    ]
  },
  "style_id": "apa",
  "options": {
    "output_format": "docx",
    "page_size": "A4",
    "font_family": "Times New Roman",
    "font_size": 12,
    "line_spacing": 2.0,
    "include_toc": false,
    "include_page_numbers": true
  }
}
```

Response: `200 OK` — Binary DOCX file download

### Validate Manuscript

```
POST /api/v1/validate
```

Request:
```json
{
  "manuscript": { "...": "..." },
  "style_id": "apa"
}
```

Response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    {
      "code": "MISSING_KEYWORDS",
      "message": "Keywords are recommended for APA style",
      "severity": "warning"
    }
  ],
  "suggestions": [
    "Consider adding a 'Methodology' section"
  ]
}
```

### Generate Preview

```
POST /api/v1/preview
```

Request: Same as format but returns HTML.

Response:
```json
{
  "html": "<!DOCTYPE html>...",
  "style_applied": "apa"
}
```

### List Styles

```
GET /api/v1/styles
```

Response:
```json
[
  {
    "id": "apa",
    "name": "APA 7th Edition",
    "version": "7.0",
    "description": "American Psychological Association...",
    "citation_format": "apa",
    "is_builtin": true
  }
]
```

### Get Style

```
GET /api/v1/styles/{style_id}
```

Response: Single style object with full configuration fields.

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Input validation failed |
| STYLE_NOT_FOUND | 404 | Style ID not recognized |
| FORMATTING_ERROR | 422 | Formatting engine error |
| MANUSCRIPT_TOO_LARGE | 413 | File exceeds size limit |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Unexpected server error |

## Rate Limiting

- Format: 10 req/min
- Validate: 30 req/min
- Preview: 20 req/min
- Styles: 60 req/min

Rate limit headers are returned on all responses.
