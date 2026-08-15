# SDK Guide

Welcome to the ScholarFormAI SDK Guide. This document provides an overview of how to integrate the ScholarFormAI SDKs into your applications.

## Supported Languages

We currently offer official SDKs for the following languages:

- **Python** (>= 3.8)
- **Node.js** (>= 16)
- **Go** (>= 1.19)

## Python SDK

### Installation

```bash
pip install scholarform-sdk
```

### Basic Usage

```python
from scholarform import Client

client = Client(api_key="YOUR_API_KEY")

# Format a document synchronously
response = client.format_document(
    file_path="thesis.docx",
    template="mla-9"
)

# Save the output
with open("thesis_formatted.docx", "wb") as f:
    f.write(response.read())
```

## Node.js SDK

### Installation

```bash
npm install @scholarform/sdk
```

### Basic Usage

```javascript
const { ScholarFormClient } = require('@scholarform/sdk');

const client = new ScholarFormClient({ apiKey: 'YOUR_API_KEY' });

async function formatMyDoc() {
  const result = await client.formatDocument({
    filePath: 'thesis.docx',
    template: 'mla-9'
  });

  await result.saveAs('thesis_formatted.docx');
}

formatMyDoc();
```

## Best Practices

1. **Keep API Keys Secure**: Never hardcode API keys in your source code. Use environment variables.
2. **Handle Rate Limits**: The SDKs automatically handle 429 errors with exponential backoff by default.
3. **Use Asynchronous Methods**: For large documents, prefer asynchronous submission and webhooks to avoid timeouts.

## Related Documentation

- [API Reference](../api/API_REFERENCE.md)
- [Plugin Guide](PLUGIN_GUIDE.md)
