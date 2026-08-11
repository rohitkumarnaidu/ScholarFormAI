<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Quickstart Guide
description: Get ScholarForm AI running in 5 minutes
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: monthly
last_updated: July 2026
---

# Quickstart Guide

Get ScholarForm AI running in 5 minutes.

## 1. Prerequisites

- Python 3.12
- Node.js 20+
- Git

## 2. Clone & Setup Backend

```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd scholarform/backend

# Create virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Copy environment file
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

## 3. Start Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` — Swagger UI.

## 4. Setup Frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## 5. Verify

```bash
# Health check
curl http://localhost:8000/api/v1/health
# → {"status":"ok","services":{...}}

# List templates
curl http://localhost:8000/api/v1/templates
# → [{"id":"ieee","name":"IEEE"}, ...]
```

## 6. Format Your First Document

1. Open `http://localhost:3000` in your browser
2. Click **Upload Document**
3. Select a `.docx` file
4. Choose a template (e.g., IEEE)
5. Click **Format**
6. Download the formatted result

## What's Next?

| If you want to... | Go here |
| ------------------- | --------- |
| Learn the full workflow | [User Guide](user_guide.md) |
| Try the AI Agent | [Agent Docs](../agents/Agent.md) |
| Create a template | [Template Creation](template_creation.md) |
| Deploy to production | [Deployment Guide](../deployment/Deployment.md) |
| Contribute code | [CONTRIBUTING.md](../../CONTRIBUTING.md) |
| See working examples | [examples/](../examples/) |

---

## See Also

- [Architecture Overview](../architecture/ARCHITECTURE.md)
- [API Reference](API.md)
- [Troubleshooting](../operations/TROUBLESHOOTING.md)
