# SDK Guide

## Installation

```bash
pip install amf-sdk
```

## Quick Start

```python
from amf_sdk import AMFClient, Manuscript, Author, Section, Paragraph

client = AMFClient()

# Create a manuscript
manuscript = Manuscript(
    title="My Research Paper",
    authors=[Author(first_name="Jane", last_name="Smith")],
    abstract="This is the abstract.",
    keywords=["research", "science"],
    sections=[
        Section(
            heading="Introduction",
            level=1,
            content=[Paragraph(text="This is the introduction.")],
        ),
    ],
)

# Format it
result = client.format_manuscript(manuscript, style="apa")
print(f"Formatted: {result.pages} pages")

# Validate it
validation = client.validate_manuscript(manuscript, style="mla")
print(f"Valid: {validation.valid}")

# List styles
styles = client.get_styles()
for style in styles:
    print(f"{style.id}: {style.name}")

# Get preview
html = client.get_preview(manuscript, style="chicago")
```

## Async Client

```python
import asyncio
from amf_sdk.async_client import AsyncAMFClient

async def main():
    async with AsyncAMFClient() as client:
        styles = await client.get_styles()
        print(styles)

asyncio.run(main())
```

## Configuration

```python
# Custom API endpoint
client = AMFClient(base_url="https://amf.example.com")

# With API key
client = AMFClient(base_url="https://amf.example.com", api_key="sk-...")

# Custom timeout
client = AMFClient(timeout=60.0)
```

## Error Handling

```python
from amf_sdk import AMFClient
from amf_sdk.exceptions import (
    AMFValidationError,
    AMFFormattingError,
    AMFConnectionError,
)

client = AMFClient()

try:
    result = client.format_manuscript(manuscript)
except AMFValidationError as e:
    print(f"Validation error: {e}")
except AMFFormattingError as e:
    print(f"Formatting error: {e}")
except AMFConnectionError as e:
    print(f"Connection error: {e}")
```

## Models

### Manuscript

| Field | Type | Required |
|-------|------|----------|
| title | str | Yes |
| authors | List[Author] | No |
| abstract | Optional[str] | No |
| keywords | List[str] | No |
| sections | List[Section] | No |
| references | List[Reference] | No |
| acknowledgments | Optional[str] | No |

### Author

| Field | Type | Required |
|-------|------|----------|
| first_name | str | Yes |
| last_name | str | Yes |
| affiliation | Optional[str] | No |
| email | Optional[str] | No |
| orcid | Optional[str] | No |

### Section

| Field | Type | Required |
|-------|------|----------|
| heading | str | Yes |
| level | int | No (default: 1) |
| content | List[Paragraph] | No |
| subsections | List[Section] | No |

## API Methods

| Method | Description |
|--------|-------------|
| `format_manuscript(ms, style, options)` | Format a manuscript |
| `format_from_file(path, style, options)` | Format a file |
| `validate_manuscript(ms, style)` | Validate manuscript |
| `get_styles()` | List all styles |
| `get_style(id)` | Get style details |
| `get_preview(ms, style)` | Get HTML preview |
