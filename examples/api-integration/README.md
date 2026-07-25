# API Integration Example

This example demonstrates integrating AMF's API into your application.

## Python Integration

```python
import requests
from pathlib import Path

API_URL = "http://localhost:8000/api/v1"

def format_manuscript(file_path: str, style: str = "apa") -> Path:
    """Format a manuscript file using AMF API."""
    text = Path(file_path).read_text(encoding="utf-8")
    
    payload = {
        "manuscript": {
            "title": Path(file_path).stem,
            "sections": [{
                "heading": "Content",
                "level": 1,
                "content": [{"text": text}]
            }]
        },
        "style_id": style
    }
    
    response = requests.post(
        f"{API_URL}/format",
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    
    output_path = Path(f"output_{Path(file_path).stem}_{style}.docx")
    output_path.write_bytes(response.content)
    return output_path

# Usage
result = format_manuscript("paper.md", "apa")
print(f"Formatted: {result}")
```

## JavaScript Integration

```javascript
async function formatManuscript(text, style = 'apa') {
  const response = await fetch('http://localhost:8000/api/v1/format', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      manuscript: {
        title: 'My Paper',
        sections: [{
          heading: 'Content',
          level: 1,
          content: [{ text }]
        }]
      },
      style_id: style
    })
  });

  if (!response.ok) throw new Error('Formatting failed');
  
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `manuscript_${style}.docx`;
  a.click();
}
```

## CI/CD Integration

```yaml
# GitHub Actions
name: Format Manuscripts
on: [push]
jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          for file in manuscripts/*.md; do
            curl -X POST http://your-api/api/v1/format \
              -H "Content-Type: application/json" \
              -d "{\"manuscript\": {\"title\": \"$(basename $file .md)\", \"sections\": []}, \"style_id\": \"apa\"}" \
              -o "formatted/$(basename $file .md).docx"
          done
      - uses: actions/upload-artifact@v4
        with:
          name: formatted-manuscripts
          path: formatted/
```
