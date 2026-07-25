# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Endpoints

### `POST /format`

Format a manuscript into a styled DOCX file.

**Request Body:**
```json
{
  "manuscript": {
    "title": "string (required)",
    "authors": [
      {
        "first_name": "string",
        "last_name": "string",
        "affiliation": "string (optional)",
        "email": "string (optional)",
        "orcid": "string (optional)"
      }
    ],
    "abstract": "string (optional)",
    "keywords": ["string"],
    "sections": [
      {
        "heading": "string",
        "level": "integer (1-6)",
        "content": [{"text": "string", "style": "string (optional)", "alignment": "string (optional)"}],
        "subsections": ["Section (recursive)"]
      }
    ],
    "references": [
      {
        "authors": ["Author"],
        "year": "string",
        "title": "string",
        "journal": "string (optional)",
        "volume": "string (optional)",
        "issue": "string (optional)",
        "pages": "string (optional)",
        "doi": "string (optional)"
      }
    ],
    "acknowledgments": "string (optional)",
    "funding_statement": "string (optional)",
    "conflict_of_interest": "string (optional)"
  },
  "style_id": "string (default: 'apa')",
  "options": {
    "output_format": "'docx' | 'pdf'",
    "page_size": "'A4' | 'Letter' | 'Legal'",
    "font_family": "string",
    "font_size": "number",
    "line_spacing": "number",
    "margins": {"top": "number", "bottom": "number", "left": "number", "right": "number"},
    "include_toc": "boolean",
    "include_page_numbers": "boolean",
    "include_running_header": "boolean"
  }
}
```

**Response:** `200 OK` — Binary DOCX file download

### `POST /validate`

Validate manuscript structure and style compliance.

**Request:**
```json
{
  "manuscript": { "...": "Manuscript object" },
  "style_id": "string"
}
```

**Response:**
```json
{
  "valid": "boolean",
  "errors": [{"code": "string", "message": "string", "location": "string (optional)", "severity": "'error' | 'warning'"}],
  "warnings": ["ValidationIssue"],
  "suggestions": ["string"]
}
```

### `POST /preview`

Generate HTML preview of formatted manuscript.

**Request:** Same as format.

**Response:**
```json
{
  "html": "string (HTML content)",
  "style_applied": "string"
}
```

### `GET /styles`

List all available formatting styles.

**Response:**
```json
[
  {
    "id": "string",
    "name": "string",
    "version": "string",
    "description": "string",
    "citation_format": "string",
    "is_builtin": "boolean"
  }
]
```

### `GET /styles/{id}`

Get details for a specific style.

**Response:** Single StyleInfo object.

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| VALIDATION_ERROR | 400 | Input validation failed |
| STYLE_NOT_FOUND | 404 | Style not recognized |
| FORMATTING_ERROR | 422 | Formatting engine error |
| MANUSCRIPT_TOO_LARGE | 413 | File exceeds size limit |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
