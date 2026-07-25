# Using the SDK

## Installation

```bash
pip install amf-sdk
```

## Quick Start

```python
from amf_sdk import AMFClient, Manuscript

client = AMFClient()

# Create manuscript
manuscript = Manuscript(
    title="My Paper",
    authors=[{"first_name": "Jane", "last_name": "Smith"}],
    sections=[{
        "heading": "Introduction",
        "level": 1,
        "content": [{"text": "Hello world"}]
    }],
)

# Format it
result = client.format_manuscript(manuscript, style="apa")
print(f"Pages: {result.pages}")

# Validate
validation = client.validate_manuscript(manuscript, style="mla")
print(f"Valid: {validation.valid}")

# List styles
styles = client.get_styles()
for s in styles:
    print(f"{s.id}: {s.name}")
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

## File Operations

```python
# Format a file
result = client.format_from_file("manuscript.md", style="apa")

# Validate a file
text = open("manuscript.md").read()
validation = client.validate_manuscript(
    Manuscript(title="Test", sections=[{"heading": "Content", "level": 1, "content": [{"text": text}]}]),
    style="apa"
)
```

## Configuration

```python
# Custom endpoint
client = AMFClient(base_url="https://amf.example.com")

# With API key
client = AMFClient(base_url="https://amf.example.com", api_key="sk-...")

# Custom timeout
client = AMFClient(timeout=60.0)
```
