# AMF SDK

Python SDK for the Automated Manuscript Formatter API. Provides both sync and async clients for formatting, validating, and previewing academic manuscripts.

## Installation

```bash
pip install amf-sdk
```

## Quick Start

```python
from amf_sdk import AMFClient

# Create a client pointed at your AMF server
client = AMFClient(base_url="http://localhost:8000")

# List available styles
styles = client.get_styles()

# Format a manuscript
result = client.format_manuscript(manuscript, style="mla")

# Validate
validation = client.validate_manuscript(manuscript, style="apa")

# Async usage
from amf_sdk import AsyncAMFClient

async with AsyncAMFClient() as client:
    styles = await client.get_styles()
```

## Models

The SDK provides Pydantic models for `Manuscript`, `Author`, `Section`, `Reference`, `FormattingStyle`, and more.

See [SDK guide](https://amf.dev/docs/sdk) for full documentation.
