# ScholarForm AI — Python SDK Reference Guide

The `amf-sdk` package provides Python bindings for accessing ScholarForm AI endpoints both synchronously (`AMFClient`) and asynchronously (`AsyncAMFClient`).

---

## Installation

```bash
pip install amf-sdk
```

---

## Client Usage

### 1. Synchronous Client (`AMFClient`)

```python
from amf_sdk import AMFClient, Manuscript, Author, Section, Paragraph

# Initialize client
client = AMFClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    timeout=30.0,
)

# Context manager usage
with AMFClient(api_key="your-api-key") as client:
    styles = client.get_styles()
```

### 2. Asynchronous Client (`AsyncAMFClient`)

The asynchronous client uses `httpx.AsyncClient` under the hood.

```python
import asyncio
from amf_sdk.async_client import AsyncAMFClient
from amf_sdk import Manuscript, Author, Section, Paragraph

async def main():
    async with AsyncAMFClient(base_url="http://localhost:8000") as client:
        # Get styles
        styles = await client.get_styles()
        print(f"Available styles: {[s.id for s in styles]}")

        # Construct manuscript
        manuscript = Manuscript(
            title="Async Manuscript Formatting",
            authors=[Author(first_name="Jane", last_name="Doe", email="jane@example.com")],
            sections=[
                Section(
                    heading="Introduction",
                    level=1,
                    content=[Paragraph(text="This document is processed asynchronously.")],
                )
            ],
        )

        # Format manuscript asynchronously
        result = await client.format_manuscript(manuscript, style="ieee")
        print(f"Result URL: {result.download_url}")

asyncio.run(main())
```

---

## API Client Method Reference

Both `AMFClient` (sync) and `AsyncAMFClient` (async) expose identical method interfaces:

| Method Signature | Return Type | Description |
|---|---|---|
| `format_manuscript(manuscript, style="apa", options=None)` | `ManuscriptResult` | Post manuscript object or dictionary for formatting |
| `format_from_file(file_path, style="apa", options=None)` | `ManuscriptResult` | Read text from file path and format as a manuscript |
| `validate_manuscript(manuscript, style="apa")` | `ValidationResult` | Check structural and style rule compliance |
| `get_styles()` | `List[FormattingStyle]` | Fetch list of all registered formatting styles |
| `get_style(style_id)` | `FormattingStyle` | Fetch specific style parameters by ID |
| `get_preview(manuscript, style="apa")` | `str` | Return rendered HTML preview string |
| `close()` | `None` | Close underlying HTTP connection pool |

---

## Exception Hierarchy (`amf_sdk.exceptions`)

All SDK exceptions inherit from the base `AMFError` class.

```
AMFError (base class: Exception)
├── AMFValidationError (status_code=400)
├── AMFAuthenticationError (status_code=401)
├── AMFNotFoundError (status_code=404)
├── AMFFormattingError (status_code=422)
├── AMFRateLimitError (status_code=429)
├── AMFConnectionError (status_code=503)
└── AMFTimeoutError (status_code=504)
```

### Exception Class Details

| Exception Class | HTTP Status Code | Default Message / Attributes |
|---|---|---|
| `AMFError` | 500 | Base exception with `message`, `status_code`, and `details` dict |
| `AMFValidationError` | 400 | Raised when request payload fails schema validation |
| `AMFAuthenticationError` | 401 | Raised on invalid or missing API key |
| `AMFNotFoundError` | 404 | Raised when target resource or style is not found |
| `AMFFormattingError` | 422 | Raised when formatting engine encounters structural errors |
| `AMFRateLimitError` | 429 | Includes `retry_after` parameter in `details` |
| `AMFConnectionError` | 503 | Raised on HTTP network or connection failure |
| `AMFTimeoutError` | 504 | Raised when request exceeds configured HTTP timeout |

---

## Models Reference (`amf_sdk.models`)

### Pydantic Models Overview

- **`Author`**: `first_name`, `last_name`, `affiliation`, `email`, `orcid`
- **`Paragraph`**: `text`, `style`, `alignment`
- **`Section`**: `heading`, `level` (default 1), `content` (`List[Paragraph]`), `subsections` (`List[Section]`)
- **`Reference`**: `authors` (`List[Author]`), `year`, `title`, `journal`, `volume`, `issue`, `pages`, `doi`
- **`Manuscript`**: `title`, `authors`, `abstract`, `keywords`, `sections`, `references`, `acknowledgments`
- **`FormattingOptions`**: `output_format` (`"docx"`), `page_size` (`"A4"`), `font_family`, `font_size`, `line_spacing`, `include_toc`, `include_page_numbers`, `include_running_header`
- **`FormattingStyle`**: `id`, `name`, `version`, `description`, `citation_format`, `font_family`, `font_size`, `line_spacing`, `margin_inches`, `is_builtin`
- **`ManuscriptResult`**: `download_url`, `preview_url`, `pages`, `metadata`, `style_applied`, `formatted_at`
- **`ValidationIssue`**: `code`, `message`, `location`, `severity` (`"error"` / `"warning"`)
- **`ValidationResult`**: `valid` (bool), `errors` (`List[ValidationIssue]`), `warnings` (`List[ValidationIssue]`), `suggestions` (`List[str]`)
