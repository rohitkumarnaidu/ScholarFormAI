<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---
title: ScholarForm AI — Community FAQ
description: Extended frequently asked questions covering local setup, common issues, environment tips, and troubleshooting links
sidebar_position: 2
status: ✅ Complete
owner: Docs Team
review_cadence: monthly
last_updated: July 2026
---

# Community FAQ

> **Prerequisite reading:** [Root FAQ](../../FAQ.md) for general questions. This page covers practical setup and troubleshooting topics not found in the root FAQ.

---

## Running the Project Locally

### How do I run ScholarForm AI on my local machine?

1. Clone the repository:
   ```bash
   git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
   cd ScholarFormAI
   ```
2. Set up the backend (see [Developer Setup](../../DEVELOPER_SETUP.md)):
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. Start the backend: `uvicorn app.main:app --reload`
4. Set up the frontend (see [Quickstart](../quickstart.md)):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Do I need Redis to run locally?

Redis is optional for local development. The backend runs without it, but Celery background tasks and real-time features will be unavailable. See [Celery Tasks Reference](../CELERY_TASKS_REFERENCE.md) for details.

### Do I need Docker?

Docker is only required if you want to run GROBID, Docling, or other AI microservices locally. The platform uses hosted Hugging Face Spaces by default. See [DEVELOPER_SETUP.md](../../DEVELOPER_SETUP.md) for configuration options.

### How do I test the formatting pipeline without uploading a file?

Use the example scripts in `examples/`:

```bash
cd examples/quick-format
python quick_format.py
```

See [examples/README.md](../../examples/README.md) for full usage.

---

## Common Issues and Solutions

### Backend fails to start with "ModuleNotFoundError"

Ensure you are using **Python 3.12.x**. Python 3.11 causes pytest import collisions, and 3.13+ is untested. Always activate your virtual environment before installing dependencies.

### Frontend build fails on Windows

Some native npm dependencies may require build tools. Run:

```powershell
npm install --build-from-source
```

If issues persist, check [Troubleshooting Guide](../troubleshooting.md) for Windows-specific fixes.

### "Port 8000 already in use"

Kill the existing process:

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Uploaded document fails to process

Verify your document is a valid DOCX or PDF. Check [Troubleshooting Guide](../troubleshooting.md#1-upload-errors) for known file format restrictions and size limits.

### Rate limiting errors during development

Rate limiting is enabled in production by default. In local development, set `DISABLE_RATE_LIMIT=true` in your `.env` file. See [Security](../Security.md) for rate limit configuration.

### Authentication errors when calling API

Ensure your Supabase JWT token is valid and passed as a Bearer token in the `Authorization` header. For local development without auth, see [API Key Quick Start](../API_KEY_QUICK_START.md).

---

## Environment Setup Tips

### Windows-specific setup

- Use **PowerShell 7+** or **Git Bash** for running setup scripts
- Ensure longer path support is enabled: `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD`
- Install **Visual Studio Build Tools** with `Desktop development with C++` workload for native modules

### GPU acceleration for local AI models

If running local LLMs with Ollama, the agent pipeline can use GPU acceleration. Configure in `backend/.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

See [LLM Provider Guide](../LLM_PROVIDER_GUIDE.md) for all supported providers.

### Environment variable management

Copy the example env files and customize:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Required variables are documented in [Developer Setup](../../DEVELOPER_SETUP.md#environment-variables). Never commit `.env` files to version control.

### Using alternative LLM providers

ScholarForm AI supports NVIDIA, Groq, Ollama, and OpenAI-compatible endpoints. No provider is required for the formatting pipeline — only for AI generation features. Configure in `backend/.env`:

```env
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-...
```

See [API Key Quick Start](../API_KEY_QUICK_START.md) for detailed setup.

---

## Troubleshooting Links

| Issue | Resource |
|-------|----------|
| Upload / processing errors | [Troubleshooting Guide](../troubleshooting.md#1-upload-errors) |
| AI generation failures | [Troubleshooting Guide](../troubleshooting.md#3-generator--synthesis-issues) |
| Authentication problems | [Troubleshooting Guide](../troubleshooting.md#6-auth--security-errors) |
| Preview / download issues | [Troubleshooting Guide](../troubleshooting.md#4-preview-problems) |
| CI pipeline failures | [CI/CD Architecture](../CI_CD_ARCHITECTURE.md) |
| Database connection errors | [Backup & Recovery](../BACKUP_RECOVERY.md) |
| High error rates in production | [High Error Rate Runbook](../runbooks/high-error-rate.md) |
| General debugging | [Debugging Guide](../../DEBUGGING.md) |

---

## Getting Help

- **GitHub Issues:** Report bugs and request features at [github.com/rohitkumarnaidu/ScholarFormAI/issues](https://github.com/rohitkumarnaidu/ScholarFormAI/issues)
- **Discussions:** Join the community at [github.com/rohitkumarnaidu/ScholarFormAI/discussions](https://github.com/rohitkumarnaidu/ScholarFormAI/discussions)
- **Email:** `@scholarform.ai`
- **Support Tiers:** See [SUPPORT.md](../../SUPPORT.md) for SLA details
