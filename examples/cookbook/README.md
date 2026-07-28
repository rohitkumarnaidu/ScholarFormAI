# AMF Cookbook

Practical recipes for common academic manuscript formatting and API integration use cases.

## Recipes

### 1. Basic Formatting via CLI

```bash
amf format -i paper.docx -s ieee -o formatted_ieee.docx
```

### 2. Format with Validation

```bash
amf validate -i paper.docx -s ieee && amf format -i paper.docx -s ieee -o formatted_ieee.docx
```

### 3. Multiple Styles Comparison Loop

```bash
for style in apa mla chicago ieee springer acm; do
    amf format -i paper.docx -s "$style" -o "paper_${style}.docx"
done
```

### 4. Watch Mode for Active Editing

```bash
amf format -i paper.md -s ieee -o output/paper.docx --watch
```

### 5. Generate and Open Preview

```bash
amf preview -i paper.md -s ieee --open
```

### 6. Convert Manuscript to Multiple Export Formats

```bash
# Markdown / DOCX → DOCX (IEEE format)
amf format -i manuscript.md -s ieee -o manuscript_ieee.docx

# Markdown / DOCX → PDF Export
amf format -i manuscript.md -s ieee -o manuscript_ieee.pdf --format pdf

# Markdown / DOCX → LaTeX Export
amf format -i manuscript.md -s ieee -o manuscript_ieee.tex --format tex
```

### 7. Team Project Setup (Starter Kit Initialization)

```bash
amf init -n team-project -s ieee
cd team-project
git init
git add .
git commit -m "Initial project setup with ScholarForm AI starter kit"
```

### 8. Python SDK Usage (`AMFClient` & `AsyncAMFClient`)

```python
from amf_sdk import AMFClient

client = AMFClient(api_url="http://localhost:8000")

# Health Check
health = client.health()
print("Backend status:", health.get("status"))

# Upload document
result = client.upload_document("paper.docx", template="ieee")
job_id = result["job_id"]

# Wait for completion & download
completed = client.wait_for_completion(job_id)
output_path = client.download_document(job_id, "formatted_paper.docx")
print("Saved to:", output_path)
```

### 9. API-Based Integration using cURL and `jq` (`api_envelope`)

```bash
#!/bin/bash
API_URL="${API_URL:-http://localhost:8000/api/v1}"

format_manuscript() {
    local file="$1"
    local template="${2:-ieee}"
    
    # 1. Upload
    res=$(curl -s -X POST "$API_URL/documents/upload" \
        -F "file=@$file" \
        -F "template=$template")
    
    job_id=$(echo "$res" | jq -r '.data.job_id')
    echo "Processing job $job_id..."

    # 2. Wait for completion
    status="processing"
    while [ "$status" != "completed" ]; do
        sleep 1
        status_res=$(curl -s "$API_URL/documents/$job_id/status")
        status=$(echo "$status_res" | jq -r '.data.status | ascii_downcase')
    done

    # 3. Download
    curl -s "$API_URL/documents/$job_id/download?format=docx" \
        -o "$(basename $file .docx)_${template}.docx"
    echo "Downloaded formatted output."
}

format_manuscript "paper.docx" "ieee"
```

### 10. Docker-Based CI Pipeline

```yaml
# docker-compose.ci.yml
services:
  amf-cli:
    image: python:3.12
    command: >
      sh -c "pip install amf-cli &&
             amf format -i /manuscripts/paper.docx -s ieee -o /output/paper_ieee.docx"
    volumes:
      - ./manuscripts:/manuscripts
      - ./output:/output
```
