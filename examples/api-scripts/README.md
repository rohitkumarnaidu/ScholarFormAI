<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# API Scripts Examples

Client scripts for interacting with ScholarForm API programmatically.

## Python Client

```bash
pip install requests
python scholarform_client.py --api-key YOUR_KEY "paper.docx" --template ieee
```

## JavaScript Client

```bash
node scholarform_client.js --api-key YOUR_KEY "paper.docx" --template ieee
```

## Quick Reference

```python
import requests

BASE = "http://localhost:8000"
headers = {"Authorization": "Bearer YOUR_API_KEY"}

# Health check
r = requests.get(f"{BASE}/api/v1/health")
print(r.json())

# List templates
r = requests.get(f"{BASE}/api/v1/templates")
print([t["name"] for t in r.json()])

# Upload and format
with open("paper.docx", "rb") as f:
    r = requests.post(
        f"{BASE}/api/v1/documents/upload",
        headers=headers,
        files={"file": ("paper.docx", f)},
        data={"template": "ieee"},
    )
job_id = r.json()["job_id"]
print(f"Job: {job_id}")
```
