# Quick Start

## Using the Web UI

1. Open [http://localhost:3000](http://localhost:3000)
2. Click **Format** in the navigation
3. Paste or type your manuscript in the editor
4. Select a citation style (APA, MLA, Chicago, etc.)
5. Adjust formatting options
6. Click **Download DOCX** or **Preview**

## Using the CLI

```bash
# Create a new project
amf init -n my-research-paper

# Navigate to project
cd my-research-paper

# Edit the manuscript (use your preferred editor)
vim manuscript.md

# Format it
amf format -i manuscript.md -s apa -o paper.docx

# Validate before formatting
amf validate -i manuscript.md -s apa
```

## Using the API

```bash
curl -X POST http://localhost:8000/api/v1/format \
  -H "Content-Type: application/json" \
  -d '{
    "manuscript": {
      "title": "My Research Paper",
      "authors": [{"first_name": "Jane", "last_name": "Smith"}],
      "abstract": "This paper explores...",
      "sections": [
        {
          "heading": "Introduction",
          "level": 1,
          "content": [{"text": "This is the introduction."}]
        }
      ]
    },
    "style_id": "mla"
  }' --output paper.docx
```

## Using the SDK

```python
from amf_sdk import AMFClient, Manuscript, Author, Section, Paragraph

client = AMFClient()

manuscript = Manuscript(
    title="My Research Paper",
    authors=[Author(first_name="Jane", last_name="Smith")],
    abstract="This is the abstract.",
    sections=[
        Section(
            heading="Introduction",
            level=1,
            content=[Paragraph(text="Start writing here.")],
        ),
    ],
)

result = client.format_manuscript(manuscript, style="apa")
print(f"Formatted: {result.pages} pages")
```
