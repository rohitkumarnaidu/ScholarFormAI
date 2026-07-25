<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Glossary
description: Terminology reference for common terms used across the project
sidebar_position: 90
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# Glossary

| Term | Definition |
|------|------------|
| **ADR** | Architecture Decision Record — a document that captures an important architectural decision made along with its context and consequences |
| **Agent** | AI-powered assistant that generates academic manuscripts through an 11-step pipeline (task parsing → outline → writing → citations → quality → export) |
| **Alembic** | Database migration tool for SQLAlchemy used to manage schema changes |
| **App Router** | Next.js 16 routing paradigm based on file-system routing with `layout.jsx` and `page.jsx` files |
| **Celery** | Distributed task queue for background job processing (document formatting, AI generation) |
| **ChromaDB** | Open-source vector database used for RAG (Retrieval-Augmented Generation) — stores document embeddings per session |
| **ClamAV** | Open-source antivirus engine used to scan uploaded files before processing |
| **Contract** | A `contract.yaml` file in a template folder that declares required Jinja variables, supported options, and output constraints |
| **CSL** | Citation Style Language — an XML-based language to describe citation formatting (10,000+ styles supported) |
| **DOCX** | Microsoft Word Open XML Document format — primary input and output format |
| **Docling** | IBM's document understanding library — used as the 2nd-tier PDF parser fallback |
| **FastAPI** | Python web framework used for all backend API routes |
| **GROBID** | GeneRation Of BIbliographic Data — ML-based PDF metadata extraction service |
| **Jinja2** | Template engine used to embed variables (`{{ title }}`) and control flow (`{% for %}`) in DOCX templates |
| **JWT** | JSON Web Token — used for API authentication via Supabase |
| **LiteLLM** | Python library that provides a unified interface across multiple LLM providers (NVIDIA, Groq, Ollama) |
| **LLM** | Large Language Model — AI model used for text generation (NVIDIA NIM, Groq, DeepSeek) |
| **Mermaid** | Markdown-based diagramming language used for flowcharts, sequence diagrams, and architecture views |
| **NVIDIA NIM** | NVIDIA's model inference microservice — primary LLM provider (Llama 3.3 70B) |
| **PITR** | Point-In-Time Recovery — continuous database backup that allows restoration to any timestamp |
| **Playwright** | End-to-end testing framework used for browser-level tests |
| **RAG** | Retrieval-Augmented Generation — technique of retrieving relevant document chunks before LLM generation |
| **RBAC** | Role-Based Access Control — authorization mechanism (admin, pro, free, guest roles) |
| **Render** | Cloud platform hosting the backend API, Celery worker, and Redis |
| **RLS** | Row-Level Security — PostgreSQL feature used by Supabase to scope data access per user |
| **RPO** | Recovery Point Objective — maximum acceptable data loss in a disaster (1 hour) |
| **RTO** | Recovery Time Objective — maximum acceptable downtime in a disaster (4 hours) |
| **LLMClassifier** | Scientific BERT model for classifying document sections (IMRaD) — disabled by default |
| **SSE** | Server-Sent Events — HTTP-based streaming protocol used for real-time processing progress |
| **Supabase** | Backend-as-a-Service providing PostgreSQL database, authentication, and file storage |
| **Synthesis** | Feature that combines 2-6 source PDFs into a single coherent manuscript |
| **Template** | A journal-specific formatting guide consisting of `template.docx`, `contract.yaml`, and optional `styles.csl` |
| **TipTap** | Rich text editor component used on the `/edit` page for manuscript editing |
| **Uvicorn** | ASGI server used to run the FastAPI application |
| **Vercel** | Cloud platform hosting the Next.js frontend application |
| **Vitest** | Unit test framework for the frontend (Vite-native, used with jsdom) |
| **WebSocket** | Protocol used for real-time live preview connection |
