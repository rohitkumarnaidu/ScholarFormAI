# Validation

## Why Validate?

Validation catches common issues before formatting:

- Missing required sections (abstract, keywords)
- Structural problems (empty sections, unheaded content)
- Reference completeness (missing DOIs, incomplete entries)
- Style compliance (required elements per citation style)

## CLI

```bash
# Basic validation
amf validate -i manuscript.md -s apa

# Save report
amf validate -i manuscript.md -s apa -o report.json
```

## API

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "manuscript": {"title": "Test", "sections": []},
    "style_id": "apa"
  }'
```

## Error Severity

| Severity | Meaning |
| ---------- | --------- |
| `error` | Must be fixed before formatting |
| `warning` | Recommended to fix |
| `suggestion` | Optional improvement |

## Common Issues

1. **Missing title** — Every manuscript needs a title
2. **No abstract** — Required for APA, MLA, Chicago, Vancouver, AMA
3. **Missing authors** — At least one author required
4. **No references** — Academic papers should cite sources
5. **Empty sections** — Sections without content
