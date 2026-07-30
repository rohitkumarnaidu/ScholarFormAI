# Using the API

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Optional API key:

```bash
curl -H "Authorization: Bearer your-api-key" https://api.example.com/api/v1/styles
```

## Endpoints

### Format Manuscript

```bash
curl -X POST http://localhost:8000/api/v1/format \
  -H "Content-Type: application/json" \
  -d '{
    "manuscript": {
      "title": "My Paper",
      "authors": [{"first_name": "Jane", "last_name": "Smith"}],
      "abstract": "This paper explores...",
      "sections": [{
        "heading": "Introduction",
        "level": 1,
        "content": [{"text": "This is the introduction."}]
      }]
    },
    "style_id": "apa",
    "options": {
      "page_size": "A4",
      "line_spacing": 2.0
    }
  }' \
  --output formatted.docx
```

### Validate Manuscript

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "manuscript": {"title": "Test", "sections": []},
    "style_id": "apa"
  }'
```

### Generate Preview

```bash
curl -X POST http://localhost:8000/api/v1/preview \
  -H "Content-Type: application/json" \
  -d '{
    "manuscript": {"title": "Test", "sections": [{"heading": "Intro", "level": 1, "content": [{"text": "Hello"}]}]},
    "style_id": "mla"
  }'
```

### List Styles

```bash
curl http://localhost:8000/api/v1/styles
```

## Error Handling

All errors return:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "details": {}
}
```

## Rate Limiting

- Format: 10 req/min
- Validate: 30 req/min
- Preview: 20 req/min
