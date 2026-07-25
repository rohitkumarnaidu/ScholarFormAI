# AMF Cookbook

Practical recipes for common use cases.

## Recipes

### 1. Basic Formatting

```bash
amf format -i paper.md -s apa -o paper.docx
```

### 2. Format with Validation

```bash
amf validate -i paper.md -s apa && amf format -i paper.md -s apa -o paper.docx
```

### 3. Multiple Styles Comparison

```bash
for style in apa mla chicago ieee; do
    amf format -i paper.md -s "$style" -o "paper_${style}.docx"
done
```

### 4. Watch Mode for Active Editing

```bash
amf format -i paper.md -s apa -o paper.docx --watch
```

### 5. Generate and Open Preview

```bash
amf preview -i paper.md -s apa --open
```

### 6. Convert Markdown to Multiple Formats

```bash
# Markdown → DOCX (APA)
amf format -i paper.md -s apa -o paper_apa.docx

# Markdown → HTML Preview
amf preview -i paper.md -s apa -o paper_preview.html
```

### 7. Team Project Setup

```bash
amf init -n team-project -s ieee
cd team-project
git init
git add .
git commit -m "Initial project setup"
```

### 8. Docker-Based CI

```yaml
# docker-compose.ci.yml
services:
  amf-cli:
    image: python:3.12
    command: >
      sh -c "pip install amf-cli &&
             amf format -i manuscript.md -s apa -o output.docx"
    volumes:
      - ./manuscripts:/manuscripts
      - ./output:/output
```

### 9. Python Script with SDK

```python
from amf_sdk import AMFClient, Manuscript, Author, Section, Paragraph

def create_and_format_paper(title, authors_text, sections_text):
    client = AMFClient()
    
    authors = []
    for a in authors_text.split(","):
        parts = a.strip().split(" ")
        authors.append(Author(first_name=parts[0], last_name=parts[1]))
    
    sections = []
    for heading, text in sections_text.items():
        sections.append(Section(
            heading=heading,
            level=1,
            content=[Paragraph(text=text)]
        ))
    
    manuscript = Manuscript(
        title=title,
        authors=authors,
        sections=sections,
    )
    
    return client.format_manuscript(manuscript, style="apa")
```

### 10. API-Based Integration

```bash
#!/bin/bash
# API wrapper script
API_URL="${API_URL:-http://localhost:8000}"

format_manuscript() {
    local file="$1"
    local style="${2:-apa}"
    
    curl -s -X POST "$API_URL/api/v1/format" \
        -H "Content-Type: application/json" \
        -d "{\"manuscript\": {\"title\": \"$(basename $file .md)\", \"sections\": [{\"heading\": \"Content\", \"level\": 1, \"content\": [{\"text\": \"$(cat $file | jq -Rs .)\"}]}]}, \"style_id\": \"$style\"}" \
        -o "$(basename $file .md)_${style}.docx"
}

format_manuscript "paper.md" "apa"
```
