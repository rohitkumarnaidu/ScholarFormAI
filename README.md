<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

<div align="center">
  <br />
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://via.placeholder.com/200x200/1a202c/ffffff?text=ScholarForm+AI+Logo">
    <img src="https://via.placeholder.com/200x200/ffffff/1a202c?text=ScholarForm+AI+Logo" alt="ScholarForm AI Logo" width="150" height="150">
  </picture>
  <br />
  <h1>ScholarForm AI</h1>
  <h3>Automated Academic Manuscript Formatting & Generation — Powered by Agentic AI</h3>
  <p>Upload a raw manuscript and instantly receive a publisher-ready document. Or use the AI Generator to author complete, rigorously cited research papers from scratch.</p>
  
  <p>
    <a href="https://scholarform.ai/docs"><strong>Documentation</strong></a> ·
    <a href="https://scholarform.ai/demo"><strong>Live Demo</strong></a> ·
    <a href="https://scholarform.ai/api"><strong>API Reference</strong></a> ·
    <a href="https://github.com/rohitkumarnaidu/ScholarFormAI/issues"><strong>Report Bug</strong></a>
  </p>

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Build Status](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/rohitkumarnaidu/ScholarFormAI/actions/workflows/backend-ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)](docs/testing/VERIFICATION_STRATEGY.md)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](docs/release/RELEASE_CHECKLIST.md)
[![Release Status](https://img.shields.io/badge/status-GA-success.svg)](docs/release/RELEASE_CHECKLIST.md)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/rohitkumarnaidu/ScholarFormAI/badge)](https://api.scorecard.dev/projects/github.com/rohitkumarnaidu/ScholarFormAI)
[![SLSA 3](https://img.shields.io/badge/SLSA-Level_3-brightgreen)](.github/workflows/slsa-provenance.yml)

<br/>
<img src="https://via.placeholder.com/1000x500?text=ScholarForm+AI+Dashboard+Screenshot" alt="ScholarForm AI Dashboard Overview" width="100%">
<br/>
</div>

---

## 🌟 Project Vision

To eliminate formatting friction and repetitive manual labor in academic publishing, allowing researchers to focus entirely on scientific discovery.

## 🎯 Mission

Provide a robust, enterprise-grade open-source platform that leverages multi-agent AI architectures to automate manuscript formatting, reference resolution, and document synthesis.

---

## ✨ Features

- **🪄 One-Click Formatter:** Upload DOCX, PDF, LaTeX, Markdown, or HTML. Receive publisher-ready outputs in IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, and more (17+ templates).
- **🤖 Autonomous AI Generator:** An agentic AI workflow that constructs complete research documents from a prompt, supporting iterative outline approval and real-time streaming.
- **📚 Multi-Doc RAG Synthesis:** Merge, synthesize, and cross-reference content from multiple source documents into a single, cohesive manuscript using advanced Retrieval-Augmented Generation.
- **⚡ Real-Time Split-Pane Editor:** Live, real-time before/after diff editor powered by WebSockets/SSE.
- **🧠 3-Tier PDF Extraction:** Bulletproof parsing via Vision API fallback → PyMuPDF+LLM enrichment → raw PyMuPDF.
- **🛡️ Enterprise Security:** Built to SLSA Level 3 standards. Comprehensive rate limiting, RBAC, CSRF protection, and supply chain security (SBOMs, CodeQL, Scorecards).

---

## 🏗 Architecture Overview

ScholarForm AI employs a decoupled, highly scalable architecture combining a Next.js App Router frontend with an asynchronous FastAPI backend, orchestrated via Celery and Redis.

### System Diagram
```mermaid
flowchart TB
    subgraph BROWSER["Frontend Layer (Next.js 16)"]
        UI["Live Editor / Dashboard"]
        AuthUI["Supabase Auth"]
    end

    subgraph GATEWAY["API Gateway (FastAPI)"]
        G_Auth["JWKS / RBAC"]
        G_RL["Rate Limiter"]
    end

    subgraph BACKEND["Backend Services Layer"]
        direction LR
        S_Format["Formatting Engine (48 Services)"]
        S_Agent["AI Orchestrator (Agents)"]
        S_Extract["3-Tier Extraction"]
    end

    subgraph WORKERS["Async Workers"]
        C_Worker["Celery Tasks"]
        C_Stream["SSE / WebSocket"]
    end

    subgraph DATA["Data & AI Layer"]
        DB["Supabase (PostgreSQL)"]
        R_Cache["Redis Cache / PubSub"]
        V_Store["ChromaDB (Vector RAG)"]
        LLM["NVIDIA NIM / Groq / Ollama"]
    end

    UI <--> GATEWAY
    AuthUI <--> DB
    GATEWAY --> BACKEND
    BACKEND <--> WORKERS
    BACKEND <--> DATA
    WORKERS <--> DATA
```

### Architecture Diagram
```mermaid
graph TD
    Client(Browser) --> API[FastAPI Gateway]
    API --> Services[Backend Microservices]
    Services --> DB[(PostgreSQL)]
    Services --> Cache[(Redis)]
    Services --> VectorDB[(ChromaDB)]
```

---

## 🛠 Technology Stack

- **Frontend:** Next.js 16 (App Router), React 19, Tailwind CSS v3, TanStack Query v5, Zustand, Playwright
- **Backend:** Python 3.12, FastAPI, Celery, Uvicorn, Pydantic v2
- **Data & Cache:** Supabase (PostgreSQL), Redis 7.x, ChromaDB (Vector Store)
- **AI / LLMs:** NVIDIA NIM (Llama 3.3 70B), Groq (llama-3.3-70b-versatile), Ollama (DeepSeek R1 for offline fallback)
- **Document Processing:** PyMuPDF, GROBID, pandoc, pdf2docx
- **DevOps & CI/CD:** Docker, GitHub Actions, Render, Prometheus/Grafana

---

## 🚀 Quick Start

Get started in under 5 minutes using Docker.

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Installation

```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd ScholarFormAI

# Copy environment variables
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```
*Edit `.env` files to include your API keys (NVIDIA, Groq, Supabase).*

```bash
docker compose -f deploy/services/docker-compose.yml up -d
```

---

## 📖 Documentation Links

- [Architecture & System Design](docs/architecture/ARCHITECTURE.md)
- [API Reference](docs/api/API.md)
- [Python SDK Guide](docs/sdk/SDK_GUIDE.md)
- [Enterprise Readiness & Deployment](docs/deployment/Deployment.md)
- [Database Schema](docs/architecture/DATABASE_SCHEMA.md)
- [Developer Onboarding](docs/developer-guide/DEVELOPER_ONBOARDING.md)

---

## 💻 CLI Tools

ScholarForm AI provides a powerful command-line interface (`amf`) for integration into CI/CD pipelines and local workflows.

```bash
# Format a document locally
amf format input.docx --template IEEE --output output.pdf

# Run an AI diagnostic check
amf analyze paper.pdf

# Update the CLI tool
amf update
```

Read the full CLI Reference in the [Documentation](docs/cli/).

---

## 🤖 AI Features

We leverage advanced multi-agent workflows:

- **Forensic Auditor Agent:** Independently verifies citations, checks equations, and identifies hallucinated references.
- **Synthesis Agent:** Merges structured data from ChromaDB into fluid, academically rigorous paragraphs.
- **Layout Agent:** Maps abstract document structures into specific template directives.

Explore agents in [docs/agents/](docs/agents/).

---

## 🗂 Folder Structure

```text
ScholarFormAI/
├── backend/                # FastAPI backend, ML pipelines, and API services
├── frontend/               # Next.js App Router UI
├── cli/                    # AMF command line tool
├── sdk/                    # Python SDK (Sync/Async)
├── docs/                   # Enterprise Architecture, API, and setup documentation
└── deploy/                 # Docker Compose, Kubernetes manifests
```

---

## ⚙️ Configuration & Development Workflow

Check out the [Configuration Reference](docs/reference/CONFIGURATION_REFERENCE.md) to set up endpoints, limiters, and environment parameters.
For building and testing, please review our [Developer Guide](docs/developer-guide/DEVELOPER_ONBOARDING.md).

---

## 🌟 Examples

Discover sample projects and manuscript conversions in the `examples/` directory.

---

## 🔐 Security

Enterprise readiness is built-in.
- **SLSA Level 3:** Build provenance and signed artifacts.
- **CodeQL & Scorecards:** Automated vulnerability scanning on every PR.
- **Dependency Management:** Renovate + SBOM generation.

Review our complete [Security Policy](SECURITY.md).

---

## 🚢 Deployment

Detailed instructions for staging, production, and scalable operations on Kubernetes or Render can be found in the [Deployment Guide](docs/deployment/Deployment.md).

---

## 🛣 Roadmap

See the full [Roadmap](docs/roadmap/Roadmap.md) for version 2.0 plans, including peer review simulations and CRDTs for collaborative editing.

---

## 🤝 Contributing

We welcome contributions! Please review our [Contributing Guidelines](CONTRIBUTING.md) and [Governance Model](GOVERNANCE.md) before submitting pull requests.

---

## 💬 Support & Community

- **Community:** Join our [Discord](https://discord.gg/scholarformai).
- **Support:** View our [Support Policy](SUPPORT.md).
- **Code of Conduct:** Review our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## ⚖️ License

ScholarForm AI is distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">
  Made with ❤️ by the ScholarForm AI Team and Open Source Contributors.
</div>
