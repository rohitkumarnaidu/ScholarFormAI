# SDK Guide

## Installation

```bash
pip install amf-sdk
```

## Client API

### AMFClient

```python
from amf_sdk import AMFClient

# Create client
client = AMFClient(base_url="http://localhost:8000", api_key=None, timeout=30.0)
```

### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `format_manuscript(ms, style, options)` | ManuscriptResult | Format a manuscript |
| `format_from_file(path, style, options)` | ManuscriptResult | Format a file |
| `validate_manuscript(ms, style)` | ValidationResult | Validate manuscript |
| `get_styles()` | list[FormattingStyle] | List all styles |
| `get_style(id)` | FormattingStyle | Get style details |
| `get_preview(ms, style)` | str | Generate HTML preview |

### AsyncAMFClient

```python
from amf_sdk.async_client import AsyncAMFClient

async with AsyncAMFClient() as client:
    result = await client.format_manuscript(ms, style="apa")
```

## Models

### Manuscript

```python
Manuscript(
    title="str",
    authors=[Author(first_name="str", last_name="str")],
    abstract="str (optional)",
    keywords=["str"],
    sections=[Section(heading="str", level=1, content=[Paragraph(text="str")])],
    references=[Reference(authors=["Author"], year="str", title="str")],
)
```

### ManuscriptResult

```python
ManuscriptResult(
    download_url="str",
    pages=0,
    metadata={},
    style_applied="str",
    formatted_at="datetime",
)
```

## Error Handling

```python
from amf_sdk.exceptions import (
    AMFValidationError,
    AMFFormattingError,
    AMFConnectionError,
    AMFNotFoundError,
    AMFRateLimitError,
)
```

## Examples

```python
# List styles
styles = client.get_styles()
for style in styles:
    print(f"{style.id}: {style.name} ({style.citation_format})")

# Validate then format
v = client.validate_manuscript(ms, style="apa")
if v.valid:
    result = client.format_manuscript(ms, style="apa")
    print(f"Formatted: {result.pages} pages")
```
