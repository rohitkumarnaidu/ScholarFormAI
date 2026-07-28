# API Integration Example

This example demonstrates integrating ScholarForm AI's `/api/v1` endpoints into your applications across Python, JavaScript, and CI/CD pipelines.

## API Response Format (`api_envelope`)

All v1 API endpoints return responses structured with the `api_envelope` schema:

```json
{
  "data": { ... },
  "error": null,
  "request_id": "req-123456",
  "timestamp": "2026-07-28T12:00:00Z"
}
```

## Python Integration

```python
import requests
import time
from pathlib import Path

API_URL = "http://localhost:8000/api/v1"

def format_manuscript(file_path: str, template: str = "ieee", output_path: str = "formatted.docx") -> Path:
    """Upload, monitor, and download formatted manuscript via ScholarForm AI API."""
    path = Path(file_path)
    
    # 1. Upload manuscript
    with open(path, "rb") as f:
        response = requests.post(
            f"{API_URL}/documents/upload",
            files={"file": (path.name, f)},
            data={"template": template},
            timeout=60
        )
    response.raise_for_status()
    payload = response.json()
    job_id = payload["data"]["job_id"]
    print(f"Uploaded successfully. Job ID: {job_id}")

    # 2. Poll status until completed
    while True:
        status_res = requests.get(f"{API_URL}/documents/{job_id}/status", timeout=10)
        status_res.raise_for_status()
        status_data = status_res.json()["data"]
        
        status = status_data["status"].lower()
        if status == "completed":
            break
        elif status == "failed":
            raise RuntimeError(f"Formatting failed: {status_data.get('error')}")
        time.sleep(1)

    # 3. Download formatted document
    dl_res = requests.get(f"{API_URL}/documents/{job_id}/download", params={"format": "docx"}, stream=True)
    dl_res.raise_for_status()
    
    out = Path(output_path)
    with open(out, "wb") as f:
        for chunk in dl_res.iter_content(chunk_size=8192):
            f.write(chunk)
            
    print(f"Saved formatted document to {out}")
    return out

# Usage
if __name__ == "__main__":
    format_manuscript("paper.docx", "ieee", "formatted_ieee.docx")
```

## JavaScript (Node.js / Web) Integration

```javascript
async function formatManuscript(fileInput, template = 'ieee') {
  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('template', template);

  // 1. Upload
  const uploadRes = await fetch('http://localhost:8000/api/v1/documents/upload', {
    method: 'POST',
    body: formData,
  });
  
  if (!uploadRes.ok) throw new Error('Upload failed');
  const uploadBody = await uploadRes.json();
  const jobId = uploadBody.data.job_id;

  // 2. Poll Status
  let status = 'processing';
  while (status !== 'completed' && status !== 'failed') {
    await new Promise(r => setTimeout(r, 1000));
    const statusRes = await fetch(`http://localhost:8000/api/v1/documents/${jobId}/status`);
    const statusBody = await statusRes.json();
    status = statusBody.data.status.toLowerCase();
  }

  if (status === 'failed') throw new Error('Formatting failed');

  // 3. Download
  const dlRes = await fetch(`http://localhost:8000/api/v1/documents/${jobId}/download?format=docx`);
  const blob = await dlRes.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `manuscript_${template}.docx`;
  a.click();
}
```

## CI/CD Integration (cURL)

```yaml
# GitHub Actions snippet
name: Format Manuscripts
on: [push]
jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          mkdir -p formatted
          for file in manuscripts/*.docx; do
            # Upload
            RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/documents/upload \
              -F "file=@$file" \
              -F "template=ieee")
            JOB_ID=$(echo $RESPONSE | jq -r '.data.job_id')
            
            # Poll status
            STATUS="processing"
            while [ "$STATUS" != "completed" ]; do
              sleep 1
              STATUS=$(curl -s http://localhost:8000/api/v1/documents/$JOB_ID/status | jq -r '.data.status | ascii_downcase')
            done
            
            # Download
            curl -s "http://localhost:8000/api/v1/documents/$JOB_ID/download?format=docx" \
              -o "formatted/$(basename $file)"
          done
      - uses: actions/upload-artifact@v4
        with:
          name: formatted-manuscripts
          path: formatted/
```
