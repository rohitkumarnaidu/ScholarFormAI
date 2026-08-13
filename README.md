# ScholarForm AI

<div align="center">
  <h3>Automated Academic Manuscript Formatting & Generation — Powered by Agentic AI</h3>
  <p>Upload a raw manuscript and instantly receive a publisher-ready document. Or use the AI Generator to author complete, rigorously cited research papers from scratch.</p>
</div>

## 🌟 Project Vision
To eliminate formatting friction and repetitive manual labor in academic publishing, allowing researchers to focus entirely on scientific discovery. We aim to provide a robust, enterprise-grade open-source platform that leverages multi-agent AI architectures to automate manuscript formatting, reference resolution, and document synthesis.

## ✨ Features
- **One-Click Formatter:** Upload DOCX, PDF, LaTeX, Markdown, or HTML. Receive publisher-ready outputs in 17+ templates (IEEE, APA, Springer, Nature, etc.).
- **Autonomous AI Generator:** Agentic AI workflow constructs research documents from a prompt, supporting iterative outline approval and real-time streaming.
- **Multi-Doc RAG Synthesis:** Merge, synthesize, and cross-reference content from multiple source documents into a cohesive manuscript.
- **Real-Time Split-Pane Editor:** Live before/after diff editor powered by WebSockets/SSE.
- **3-Tier PDF Extraction:** Bulletproof parsing via Vision API fallback → PyMuPDF+LLM enrichment → raw PyMuPDF.
- **Enterprise Security:** Built to SLSA Level 3 standards. Comprehensive rate limiting, RBAC, CSRF protection, and supply chain security.

## 📸 Screenshots
*(Insert screenshots of the dashboard, live editor, and CLI here)*

## 🏗 Architecture
ScholarForm AI employs a decoupled, highly scalable architecture combining a Next.js App Router frontend with an asynchronous FastAPI backend, orchestrated via Celery and Redis.

## 🚀 Quick Start & Installation
**Prerequisites:** Docker, Node.js 20+, Python 3.12+
```bash
git clone https://github.com/rohitkumarnaidu/ScholarFormAI.git
cd ScholarFormAI
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
docker compose -f deploy/services/docker-compose.yml up -d
```

## 💻 CLI
```bash
amf format input.docx --template IEEE --output output.pdf
amf analyze paper.pdf
```

## 🔌 API & AI Features
- **Forensic Auditor Agent:** Verifies citations and checks equations.
- **Synthesis Agent:** Merges structured data into fluid paragraphs.
- **Layout Agent:** Maps structures into template directives.

## ⚙️ Configuration & Docker
Use the `.env` files to configure NVIDIA, Groq, Supabase keys. Docker Compose is provided for local and production deployment.

## 🛠 Development & Examples
Run the backend with `uvicorn` and frontend with `npm run dev`. See the `examples/` directory for manuscript conversions.

## ❓ FAQ & Troubleshooting
- **How do I fix Docker issues?** Ensure port 8000 (backend) and 3000 (frontend) are available.
- **API limits?** Configurable via Redis rate limiter in `.env`.

## 🛣 Roadmap
Version 2.0 plans include peer review simulations and CRDTs for collaborative editing.

## 💬 Community & Contributing
Join our Discord! Read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).

## ⚖️ License
MIT License. See [LICENSE](LICENSE) for more details.
