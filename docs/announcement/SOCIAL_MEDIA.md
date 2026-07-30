<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Social Media Launch Posts — ScholarForm AI v1.0

---

## LinkedIn (Professional — ~1,000 chars)

I'm excited to share that after months of development, **ScholarForm AI v1.0 is now live** — the first open-source, AI-powered platform for automated academic manuscript formatting.

**The problem is universal:** any researcher who has submitted a paper knows the pain of reformatting for each journal's style guide. It's tedious, error-prone, and a massive time sink.

**What ScholarForm AI does:**

- Upload any manuscript (DOCX, PDF, LaTeX, Markdown) → get a publisher-ready document in any of 17 journal templates
- AI Agent generates complete research documents from a topic prompt
- Multi-doc synthesis merges 2–10 source documents into one coherent manuscript
- 12-stage pipeline with real-time preview and before/after diff

**Stack:** FastAPI + Next.js 16 + Celery + ChromaDB + Supabase

**Why open source:** We believe academic tools should be transparent, auditable, and free. MIT license, community-governed.

Check it out, star the repo, or contribute: [link]

# ScholarFormAI #OpenSource #AcademicWriting #ResearchTools #AI #MachineLearning #FastAPI #NextJS

---

## Twitter/X — Launch Thread

**Post 1:**
Formatting a manuscript for journal submission shouldn't take hours. ScholarForm AI v1.0 is here — open-source, AI-powered, 17 journal templates, seconds flat. 🧵👇

**Post 2:**
What it does:
• Upload DOCX/PDF/LaTeX → formatted in 17 styles (IEEE, APA, Nature, Elsevier, ACM, MLA, Chicago, etc.)
• AI Agent writes full papers from a prompt — outline approval, section streaming
• Multi-doc RAG synthesis merges 2–10 sources into one manuscript
• Real-time preview with before/after diff

**Post 3:**
Built with FastAPI + Next.js 16 + Celery + ChromaDB + Supabase. MIT licensed. Cosign-signed containers. SLSA L3. OpenSSF Scorecard 10/10.

Star it on GitHub → github.com/rohitkumarnaidu/ScholarFormAI

# OpenSource #AcademicWriting #Research #AI

---

## Reddit — r/programming

**Title:** ScholarForm AI v1.0 — Open-source manuscript formatting powered by AI (17 templates, FastAPI + Next.js)

**Body:**

I built ScholarForm AI to solve a problem every academic knows: formatting manuscripts for journal submission is a soul-crushing time sink. IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago — every journal has its own style, and none of them talk to each other.

**What it does:**

- **Formatter Mode** — Upload DOCX, PDF, LaTeX, Markdown, HTML, or plain text; get back a publisher-ready manuscript in 17 templates
- **Generator Mode** — AI Agent generates a complete research doc from a prompt (outline approval → section-by-section streaming)
- **Multi-Doc Synthesis** — Upload 2–10 source docs, ChromaDB-powered RAG merges them into one coherent manuscript
- **Real-time preview** with WebSocket/SSE diff

**Stack:**

- FastAPI backend with 34 REST endpoints
- Next.js 16 (App Router) + React 19 + Tailwind
- Celery workers + Redis pub/sub
- ChromaDB for RAG
- Supabase (PostgreSQL + Auth + Storage)
- 3-tier LLM fallback (NVIDIA NIM → Groq → Ollama)
- GROBID → Docling → PyMuPDF 4-tier PDF extraction

**Security:** JWKS JWT auth, CSRF protection, ClamAV scanning, Cosign-signed multi-arch containers (amd64/arm64), SLSA L3 provenance, SBOMs, OpenSSF Scorecard.

25 CI/CD workflows, 80+ docs, all MIT licensed.

[github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)

Would love feedback, issues, and PRs. Happy to answer questions about the architecture.

---

## Reddit — r/MachineLearning

**Title:** [P] ScholarForm AI v1.0 — Open-source academic paper formatter with AI generation and RAG (FastAPI, ChromaDB)

**Body:**

We released ScholarForm AI v1.0, an open-source platform for academic manuscript formatting with AI capabilities.

**AI/ML components:**

- **Agent-based document generation** — LLM agent (NVIDIA NIM Llama 3.3 70B / Groq fallback) proposes outlines, then streams each section with citations. Uses structured output + validation per section.
- **Multi-doc RAG synthesis** — ChromaDB stores document embeddings; user uploads 2–10 docs, system retrieves + deduplicates + merges into one coherent manuscript.
- **Quality scoring** — Semantic analysis of formatting compliance, citation completeness, structure correctness.
- **LLMClassifier integration** — Optional document classification (via HF Space).
- **3-tier LLM fallback:** NVIDIA NIM → Groq → DeepSeek R1 (Ollama, local/offline).

**Pipeline:**
12-stage processing: virus scan → MIME validation → parsing → structure detection → classification → formatting → equations → references → quality score → preview → export → audit.

**Tech:** FastAPI, Celery, Redis, ChromaDB, Supabase, Next.js 16.

MIT license, repo at [github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)

Would love PRs and feedback — especially on the RAG pipeline and agent generator architecture.

---

## Reddit — r/academia

**Title:** ScholarForm AI v1.0 — Open-source tool that formats manuscripts to any journal style in seconds

**Body:**

If you've ever spent a weekend reformatting a paper for a different journal, this might help.

**ScholarForm AI v1.0** is an open-source platform that does automated manuscript formatting with AI.

**What it means for researchers:**

- Upload your paper (any format — DOCX, PDF, LaTeX, Markdown) → pick a template (IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, or custom) → download the formatted result
- AI Generator writes a full paper from a topic prompt — good for literature reviews and first drafts
- Multi-doc synthesis merges several source documents (say, 5 related papers) into one coherent manuscript
- Live preview with side-by-side before/after comparison
- Batch processing for handling multiple manuscripts at once

**17 journal templates** included, with custom template creation supported.

**Privacy:** runs with Ollama for fully local processing if you want. No data leaves your machine.

**It's free.** MIT license. [github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)

Feedback, feature requests, and contributions welcome. If you're tired of fighting with reference managers and style guides, give it a try.

---

## Hacker News — Show HN

**Title:** Show HN: ScholarForm AI – Open-source academic manuscript formatting, powered by AI

**Body:**

I built ScholarForm AI because formatting papers for different journals is one of the most frustrating parts of academic writing. Every journal has different style rules, and getting citations, headings, and layout right can take hours of manual work.

**What it does:**

1. **Format any manuscript to 17 journal styles** — Upload DOCX, PDF, LaTeX, Markdown, HTML, or plain text; download a publisher-ready file. Styles: IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, and more.
2. **AI Agent generates papers from scratch** — Enter a topic, get an outline, then stream sections one by one with citations and references.
3. **Multi-document synthesis** — Upload 2-10 related documents, ChromaDB merges them into one coherent manuscript with deduplication.
4. **Real-time preview** — Before/after diff via WebSocket/SSE, inline editing.

**Why build another tool?**

Most solutions are proprietary SaaS (Overleaf, Manuscripts.ai, typeset.io). ScholarForm is MIT-licensed, self-hostable, and auditable. You can run it fully offline with Ollama.

**Stack:** FastAPI (34 routes, 26 pipeline modules) + Next.js 16 + Celery + Redis + ChromaDB + Supabase

**Security:** JWKS JWT auth, ClamAV scanning, Cosign-signed containers, SLSA L3, SBOMs.

**What I'd love feedback on:**

- The pipeline architecture (12 stages, all swappable)
- The RAG approach for multi-doc synthesis
- Template creation workflow

Repo: [github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)

---

## Dev.to

**Title:** ScholarForm AI v1.0 — Open-Source Academic Manuscript Formatting with AI

**Published at:** dev.to
**Tags:** opensource, python, webdev, ai

---

If you've ever submitted a paper to a journal, you know the pain. IEEE wants one citation format, APA another, Nature has its own rules entirely. It's hours of tedious work that has nothing to do with your research.

**ScholarForm AI v1.0** automates this entirely.

### The Core Features

**Formatter Mode** — Upload a manuscript in any format (DOCX, PDF, LaTeX, Markdown, HTML, plain text). Select from 17 journal templates. Download a formatted, publisher-ready document. That's it. The entire pipeline runs in the background with Celery — you get a job ID and poll for results, or watch the live preview update in real time.

**AI Generator Mode** — Want to draft a paper but stuck on structure? The AI Agent takes a topic prompt, proposes an outline for your approval, then streams each section one by one. It handles citations, equations, and references. Built on NVIDIA NIM Llama 3.3 70B with automatic Groq fallback.

**Multi-Doc Synthesis** — Have 5 related papers you want to merge into a coherent manuscript? Upload them all. ChromaDB powers the RAG pipeline that cross-references, deduplicates, and synthesizes them into unified output.

**Real-Time Preview** — Before/after split view with WebSocket updates. Edit the formatted output inline and re-download.

### The Tech Stack

| Layer | Technology |
| ------- | ----------- |
| Frontend | Next.js 16 (App Router), React 19, Tailwind CSS, TanStack Query |
| Backend | FastAPI (34 REST endpoints), Celery workers |
| AI/LLM | NVIDIA NIM (primary), Groq (fallback), Ollama (local) |
| Vector DB | ChromaDB |
| Database | Supabase (PostgreSQL + Auth + Storage) |
| Realtime | Redis pub/sub → WebSocket / SSE |
| PDF Pipeline | GROBID → Docling → PyMuPDF → PyPDF2 (4-tier) |
| Deployment | Render, Docker, GitHub Container Registry |

### Getting Started

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

### Open Source & Security

MIT licensed. 25 CI/CD workflows. Multi-arch container images (amd64/arm64) with Cosign signing. SLSA Level 3 build provenance. CycloneDX SBOMs for both backend and frontend. OpenSSF Scorecard evaluated.

### Get Involved

- **GitHub:** [github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)
- **Docs:** 80+ documentation files in the repo
- **Contributing:** PRs welcome — check CONTRIBUTING.md and the roadmap

---

## Product Hunt

**Tagline:** The first open-source AI platform that formats academic manuscripts to any journal style in seconds.

**Description:**

ScholarForm AI is an open-source, AI-powered platform purpose-built to eliminate the formatting nightmare of academic publishing. Upload any manuscript (DOCX, PDF, LaTeX, Markdown, HTML, plain text), select your target journal from 17 templates (IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, and more), and download a perfectly formatted, publisher-ready document.

Beyond formatting, the AI Agent generator drafts complete research papers from a topic prompt, and the Multi-Doc RAG engine merges 2–10 source documents into one coherent manuscript.

**Key Features:**

- 12-stage automated formatting pipeline
- AI paper generation with outline approval + section streaming
- Multi-document RAG synthesis with ChromaDB
- Real-time before/after preview with inline editing
- 17 journal templates (custom templates supported)
- Batch upload and parallel processing
- Fully self-hostable (Ollama support for offline use)
- 80+ documentation files

**Stack:** FastAPI + Next.js 16 + Celery + ChromaDB + Supabase + NVIDIA NIM + Groq

**Security:** MIT license, Cosign-signed containers, SLSA L3 provenance, SBOMs, OpenSSF Scorecard 10/10.

**First Message:**

> Academics spend 15–25% of their writing time on formatting. We built ScholarForm AI to give that time back.
>
> Today we're launching v1.0 — the first open-source, AI-powered manuscript formatting platform. Upload a draft, pick a journal's style guide, and get a submission-ready document in seconds.
>
> We're MIT licensed because academic tools belong in the open. Self-host it, audit it, contribute to it.
>
> Would love your feedback, questions, and ideas for the next templates to add.

**Links:**

- GitHub: [github.com/rohitkumarnaidu/ScholarFormAI](https://github.com/rohitkumarnaidu/ScholarFormAI)
- Website: [scholarform.ai](https://scholarform.ai)

**First comment:** What templates should we add next? We currently support 17 (IEEE, APA, Springer, Nature, Elsevier, ACM, MLA, Chicago, Harvard, Vancouver, Numeric, custom) — but the list is growing.
