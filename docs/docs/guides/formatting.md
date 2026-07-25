# Formatting a Manuscript

## Web UI

1. Navigate to the Format page
2. Enter or upload your manuscript text
3. Select a citation style from the dropdown
4. Configure page size, font, spacing, and margins
5. Click **Preview** to see the results
6. Click **Download DOCX** to save

## CLI

```bash
# Basic formatting
amf format -i manuscript.md -s apa -o output.docx

# With custom options
amf format -i manuscript.md -s ieee \
  -O '{"page_size": "Letter", "font_size": 10}' \
  -o output.docx

# Watch mode (auto-reformat on save)
amf format -i manuscript.md -s apa -o output.docx --watch
```

## API

```bash
curl -X POST http://localhost:8000/api/v1/format \
  -H "Content-Type: application/json" \
  -d @payload.json \
  --output formatted.docx
```

## SDK

```python
from amf_sdk import AMFClient, Manuscript

client = AMFClient()
result = client.format_from_file("manuscript.md", style="apa")
print(f"Formatted: {result.pages} pages")
```
