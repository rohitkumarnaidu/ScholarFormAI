<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---
title: ScholarForm AI — Project Glossary
description: Definitions of key terms, acronyms, and concepts used throughout the ScholarForm AI project
sidebar_position: 4
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# Project Glossary

> A reference of domain-specific terms used in the ScholarForm AI codebase and documentation.

---

## A

### Agent (AI Agent)
The 11-step AI pipeline that generates complete academic manuscripts from a user prompt. Steps include task parsing, web research, outline generation, section writing, citation insertion, and final formatting. Implemented in `backend/app/pipeline/generation/agent.py`. See [Agent Documentation](../Agent.md).

### Architecture Decision Record (ADR)
A document capturing a significant architectural decision, its context, options considered, and the chosen approach. All ADRs are in [`docs/adr/`](../adr/README.md).

## C

### Celery
Distributed task queue used for asynchronous document processing and AI generation. Routes long-running formatting and generation tasks to background workers. See [Celery Tasks Reference](../CELERY_TASKS_REFERENCE.md).

### ChromaDB
Vector database used for Retrieval-Augmented Generation (RAG). Stores embedded document chunks for semantic search during the AI generation pipeline. See [Chroma/RAG Architecture](../CHROMA_RAG_ARCHITECTURE.md).

### Contract (Template Contract)
A formal specification binding a template to a pipeline. Defines mapping rules, formatting parameters, and validation criteria. See [Template Contract System (ADR-009)](../adr/009-template-contract-system.md).

### CSL (Citation Style Language)
XML-based language used to describe citation and bibliography formatting styles. ScholarForm AI uses CSL to generate citations matching specific journal requirements.

## D

### Docling
AI-powered document understanding service used for parsing complex PDF layouts, extracting structure, tables, and figures. Deployed on Hugging Face Spaces.

### DOCX
Office Open XML document format used by Microsoft Word. ScholarForm AI's primary output format for formatted manuscripts.

## F

### FastAPI
Python web framework used for the backend API gateway. Handles all REST endpoints, WebSocket connections, middleware, and request routing. See [ADR-001](../adr/ADR-001-use-fastapi.md).

### Four-Tier LLM Fallback
Strategy for LLM provider resilience: NVIDIA (tier 1) → Groq (tier 2) → Hosted endpoint (tier 3) → Ollama local (tier 4). See [ADR-003](../adr/ADR-003-four-tier-llm-fallback.md).

## G

### GROBID (GeneRation Of Bibliographic Data)
Machine-learning service for extracting and parsing bibliographic information from PDF documents. Used in the formatting pipeline for citation and reference extraction.

## H

### Hugging Face Spaces
Hosting platform for AI microservices (GROBID, Docling, OCR, LLMPDFParser, LLMClassifier). Each service runs in a dedicated Space with GPU acceleration.

## L

### LiteLLM
Lightweight LLM routing library that provides a unified interface across multiple LLM providers (NVIDIA, Groq, Ollama, OpenAI-compatible). Handles fallback, rate limiting, and retries. See [ADR-008](../adr/008-litellm-llm-routing.md).

## M

### Manuscript
An academic paper or research document submitted for formatting. Can be uploaded as DOCX/PDF or generated from scratch via the AI agent.

### Multi-Doc Synthesis
Pipeline that combines 2-6 source PDFs into a single coherent manuscript, with deduplication, cross-referencing, and unified formatting. See [Multi-Doc Synthesis Tutorial](../tutorials/multi-doc-synthesis.md).

## N

### Next.js 16
React framework used for the frontend, with App Router for routing and server components. Hosted on Vercel. See [ADR-010](../adr/010-nextjs-app-router.md).

### LLMPDFParser (Neural Optical Understanding for Academic Documents)
Transformer-based model for OCR of academic PDFs, especially mathematical expressions. Used in the document parsing pipeline.

## O

### Ollama
Local LLM runtime for running models like Llama and Mistral on developer machines. Used as the fourth-tier fallback in the LLM routing strategy.

## P

### PDF (Portable Document Format)
Input format supported for manuscript upload. Processed via GROBID, Docling, and LLMPDFParser for structure extraction.

### Pipeline
A sequence of processing stages that transform an input manuscript into a formatted output. The formatting pipeline has 12 stages; the AI generation pipeline has 11 stages. See [Architecture](../architecture.md#formatting-pipeline).

## R

### RAG (Retrieval-Augmented Generation)
Technique used in the AI generation pipeline where relevant content is retrieved from ChromaDB and injected into the LLM context to improve output quality and factual accuracy.

### Rate Limiting
Mechanism to control API request frequency. Implemented via middleware with configurable thresholds per endpoint. See [Security](../Security.md).

### Redis
In-memory data store used for Celery message broker, WebSocket pub/sub, caching, and rate limiting counters. See [ADR-002](../adr/002-redis-realtime-backbone.md).

### Render
Cloud platform used to host the backend API (FastAPI) and Celery workers. See [ADR-007](../adr/007-render-deployment-platform.md).

### RLS (Row-Level Security)
PostgreSQL security feature used with Supabase to restrict data access at the database row level based on authenticated user identity.

## S

### SBOM (Software Bill of Materials)
Machine-readable inventory of all software components and dependencies. Generated for each release in `sbom/`. See [Reproducible Build](../REPRODUCIBLE_BUILD.md).

### LLMClassifier
BERT-based language model pre-trained on scientific text. Used for semantic understanding tasks in the document analysis pipeline.

### SLSA (Supply-chain Levels for Software Artifacts)
Security framework for verifying the integrity of software artifacts throughout the build and distribution pipeline. Target: SLSA 3.

### Supabase
Open-source Firebase alternative providing PostgreSQL database, authentication, storage, and real-time subscriptions. See [ADR-002](../adr/ADR-002-use-supabase.md).

## T

### Template
A journal-specific formatting specification (IEEE, ACM, Springer, Elsevier, etc.) defining margins, fonts, heading styles, citation format, and layout rules. ScholarForm AI supports 17+ journal templates. See [Template Creation Guide](../template_creation.md).

## V

### Vercel
Cloud platform for frontend hosting and serverless functions. Hosts the Next.js application with automatic CI/CD from the `main` branch.

## W

### WebSocket
Real-time communication protocol used for streaming AI generation progress, document processing status updates, and live preview updates.

---

## Version Information

- **Glossary Version:** 1.0
- **Last Updated:** July 2026
- **Maintainer:** Docs Team (`@scholarform.ai`)
