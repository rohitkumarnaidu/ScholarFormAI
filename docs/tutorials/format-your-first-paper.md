<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Tutorial — Format Your First Paper
description: Step-by-step tutorial to format an academic manuscript with ScholarForm AI
sidebar_position: 2
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: June 2026
---

# Tutorial: Format Your First Paper

This tutorial walks through formatting a real academic manuscript from start to finish.

## Prerequisites

- ScholarForm running locally ([Quickstart](../quickstart.md))
- A `.docx` manuscript file (or use the sample below)

## Step 1: Get a Sample Paper

Save the following as `sample-paper.docx` — or use your own manuscript.

> **Note:** If you don't have a `.docx` file, create one in Word/LibreOffice with a title, author block, abstract, and 2-3 sections with citations.

## Step 2: Choose a Template

List available templates:

```bash
curl http://localhost:8000/api/v1/templates
```

You'll see something like:
```json
[
  {"id": "ieee", "name": "IEEE", "journal": "IEEE Transactions"},
  {"id": "springer", "name": "Springer", "journal": "Springer LNCS"},
  {"id": "apa", "name": "APA 7th Edition", "journal": "APA"}
]
```

Pick `ieee` for this tutorial.

## Step 3: Upload & Format

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample-paper.docx" \
  -F "template=ieee"

# Response: {"job_id": "abc123", "status": "processing"}
```

## Step 4: Monitor Progress

```bash
curl http://localhost:8000/api/v1/documents/abc123/status

# Response: {"status": "processing", "progress": 45, "stage": "formatting"}
# Wait for: {"status": "completed", "progress": 100}
```

## Step 5: Download

```bash
curl -o ieee-formatted.docx \
  http://localhost:8000/api/v1/documents/abc123/download?format=docx
```

Open `ieee-formatted.docx` — your paper is formatted in IEEE style.

## Step 6: Try Another Template

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample-paper.docx" \
  -F "template=springer"

# Repeat steps 4-5 with the new job_id
```

Compare the two outputs. Notice how headings, spacing, and citation styles differ.

## What You Learned

- How to upload a document to ScholarForm
- How to select and apply journal templates
- How to monitor formatting progress
- How to download formatted output

## Next Steps

| Topic | Resource |
|-------|----------|
| Custom templates | [Template Creation Guide](../template_creation.md) |
| AI Agent generation | [Agent Documentation](../Agent.md) |
| Multi-doc synthesis | [User Guide](../user_guide.md) |
| API integration | [API Reference](../API.md) |
