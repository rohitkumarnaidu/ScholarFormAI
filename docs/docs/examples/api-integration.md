# API Integration Example

This example demonstrates how to integrate ScholarFormAI directly into your own application using the REST API.

## Prerequisites

- A running ScholarFormAI instance (see [Deployment](../deployment/docker.md))
- An API key (see [Authentication](../getting-started/configuration.md))
- `curl` or any HTTP client

---

## 1. Obtain an API Key

```bash
# Register and retrieve your API key from the dashboard, or via CLI:
amf api-keys create --name "my-integration"
```

---

## 2. Upload and Format a Document

```bash
curl -X POST https://your-amf-instance/api/v1/documents/format \
  -H "Authorization: Bearer $AMF_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@manuscript.docx" \
  -F "style=ieee" \
  -o formatted_output.docx
```

---

## 3. Check Job Status (Async)

For large documents the API returns a job ID:

```bash
# Submit async job
JOB_ID=$(curl -s -X POST https://your-amf-instance/api/v1/documents/format/async \
  -H "Authorization: Bearer $AMF_API_KEY" \
  -F "file=@big_manuscript.docx" \
  -F "style=apa7" | jq -r '.data.job_id')

# Poll for status
curl -H "Authorization: Bearer $AMF_API_KEY" \
  https://your-amf-instance/api/v1/jobs/$JOB_ID
```

---

## 4. Python Integration Example

```python
import httpx
import os

AMF_BASE_URL = os.environ["AMF_BASE_URL"]
AMF_API_KEY  = os.environ["AMF_API_KEY"]

def format_manuscript(input_path: str, output_path: str, style: str = "ieee") -> None:
    headers = {"Authorization": f"Bearer {AMF_API_KEY}"}
    with open(input_path, "rb") as f:
        response = httpx.post(
            f"{AMF_BASE_URL}/api/v1/documents/format",
            headers=headers,
            files={"file": f},
            data={"style": style},
            timeout=120,
        )
    response.raise_for_status()
    with open(output_path, "wb") as out:
        out.write(response.content)
    print(f"✅ Formatted document saved to {output_path}")

if __name__ == "__main__":
    format_manuscript("manuscript.docx", "formatted.docx", style="apa7")
```

---

## 5. Webhook Notifications

Register a webhook to receive a callback when formatting completes:

```bash
curl -X POST https://your-amf-instance/api/v1/webhooks \
  -H "Authorization: Bearer $AMF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.example.com/amf-webhook",
    "events": ["document.formatted", "document.failed"]
  }'
```

---

## Next Steps

- See the full [API Reference](../api/reference.md) for all endpoints.
- Learn how to use the [Python SDK](../sdk/guide.md) for a higher-level interface.
- Explore [Batch Processing](batch-processing.md) for bulk workloads.
