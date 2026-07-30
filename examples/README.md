<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI Examples & Starter Projects

Welcome to the **ScholarForm AI Examples & Templates** repository. This folder contains complete, production-ready starter kits, CLI automation scripts, API integration libraries, batch processing utilities, and cookbook recipes.

---

## 📁 Subdirectory Index (All 9 Example Kits)

| Example Subdirectory | Focus / Description | Primary Tech / Tools |
| ---------------------- | --------------------- | ---------------------- |
| 🚀 [**starter-kit**](starter-kit/README.md) | Ready-to-use project repository containing manuscript, config, bibtex, Makefile, and GitHub CI workflow. | Markdown, BibTeX, Makefile, GitHub Actions |
| ⚡ [**quick-format**](quick-format/README.md) | Single-command CLI python script (`format_paper.py`) for uploading, monitoring, and downloading formatted papers. | Python 3, `requests` |
| 🤖 [**api-scripts**](api-scripts/README.md) | Dual-language programmatic clients (`scholarform_client.py`, `scholarform_client.js`) handling `api_envelope` standards. | Python 3, Node.js (ES2022/Fetch) |
| 🔌 [**api-integration**](api-integration/README.md) | Full integration patterns for REST v1 endpoints (`/api/v1/documents/*`) across web, server, and CI/CD stacks. | Python, JavaScript, REST API |
| 📝 [**simple-formatting**](simple-formatting/README.md) | Minimal working manuscript and `amf.config.json` configuration for quick formatting checks. | Markdown, JSON |
| 📦 [**batch-processing**](batch-processing/README.md) | Shell script (`process_all.sh`) for batch formatting all manuscripts in a directory across multiple styles. | Bash, AMF CLI |
| 🔄 [**ci-integration**](ci-integration/README.md) | Ready-to-use CI/CD pipelines for GitHub Actions, GitLab CI, pre-commit hooks, and Makefile build loops. | YAML, Docker, Git |
| 🎨 [**custom-template**](custom-template/README.md) | Developer guide and contract structure for adding custom journal templates (`contract.yaml`, Jinja2 DOCX). | DOCX, YAML, Jinja2 |
| 📖 [**cookbook**](cookbook/README.md) | 10 practical recipes for watch mode, multi-style comparison, SDK usage, preview generation, and Docker builds. | CLI, SDK, Docker, cURL |

---

## 🛠️ Prerequisites & Setup

Most examples communicate with a running ScholarForm AI backend.

### 1. Start the ScholarForm AI Backend

```bash
# From repository root
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Verify the backend is running by navigating to `http://localhost:8000/api/v1/health` or inspecting the OpenAPI docs at `http://localhost:8000/docs`.

### 2. Environment Requirements

- **Python 3.12+** (with `requests`, `pyyaml`)
- **Node.js 18+** (for JavaScript API scripts)
- **Make** & **Bash** (optional, for automation scripts and Makefile build targets)

---

## 🚀 Quick Start Guide

### Option A: Create a New Paper with Starter Kit

```bash
# Copy starter kit to your workspace
cp -r examples/starter-kit my-new-paper
cd my-new-paper

# Edit your paper and references
nano manuscript.md

# Format your manuscript
make format
```

### Option B: Quick Format an Existing Paper

```bash
cd examples/quick-format
python format_paper.py --template ieee --input paper.docx --output formatted.docx
```

### Option C: Run Python or Node.js API Clients

```bash
cd examples/api-scripts

# Python Client
python scholarform_client.py paper.docx --template ieee

# Node.js Client
node scholarform_client.js paper.docx --template ieee
```

---

## 🔍 API Envelope Handling Notice

ScholarForm AI standardizes all v1 API responses using the `api_envelope` model:

```json
{
  "data": {
    "job_id": "job-abc12345",
    "status": "PROCESSING",
    "progress": 45
  },
  "error": null,
  "request_id": "req-98765",
  "timestamp": "2026-07-28T12:00:00Z"
}
```

All API client scripts in `api-scripts/`, `quick-format/`, and `api-integration/` extract the payload from `response.json()["data"]` to ensure compatibility with all v1 backend endpoints.

---

## 📁 Repository Structure Overview

```
examples/
├── README.md                 # Master index & usage guide (this file)
├── starter-kit/              # Complete manuscript template project
│   ├── manuscript.md
│   ├── amf.config.json
│   ├── references.bib
│   ├── Makefile
│   ├── .github/workflows/ci.yml
│   └── output/
├── quick-format/             # Standalone Python formatting script
│   ├── README.md
│   └── format_paper.py
├── api-scripts/              # Programmatic client scripts
│   ├── README.md
│   ├── scholarform_client.py
│   └── scholarform_client.js
├── api-integration/          # Web/REST API integration examples
│   └── README.md
├── simple-formatting/        # Minimal manuscript & config pair
│   ├── amf.config.json
│   └── manuscript.md
├── batch-processing/         # Directory batch formatting tool
│   ├── README.md
│   └── process_all.sh
├── ci-integration/           # CI/CD pipelines & hooks
│   └── README.md
├── custom-template/          # Custom journal template creation guide
│   └── README.md
└── cookbook/                 # Practical recipes & common workflows
    └── README.md
```
