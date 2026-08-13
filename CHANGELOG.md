# Changelog

All notable changes to **ScholarForm AI** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](VERSIONING.md).

## [Unreleased]
### Added
- Early alpha support for Peer Review Simulation agents.
- Experimental CRDTs for collaborative editing.

### Changed
- Refactored the core parsing engine for improved PDF extraction accuracy.

## [1.0.0] - 2026-08-13
### Added
- **One-Click Formatter:** Upload DOCX, PDF, LaTeX, Markdown, or HTML.
- **Templates:** Initial 17+ publisher templates including IEEE, APA, Springer, and Nature.
- **Autonomous AI Generator:** Agentic AI workflow for constructing research documents from prompts.
- **Multi-Doc RAG Synthesis:** Merge and cross-reference content from multiple sources.
- **Live Editor:** Real-time split-pane editor powered by WebSockets/SSE.
- **3-Tier PDF Extraction:** Vision API fallback -> PyMuPDF+LLM -> raw PyMuPDF.
- **Enterprise Security:** Implemented SLSA Level 3 standards, RBAC, CSRF protection.
- **CLI Utilities:** Introduced `amf format` and `amf analyze` commands.
- **AI Agents:** Forensic Auditor Agent, Synthesis Agent, and Layout Agent.
- **Docker Support:** Docker Compose setup for backend, frontend, Redis, and Celery.

### Security
- Comprehensive rate limiting implemented via Redis.
- Secure environment configuration templates (`.env.example`).

*See our [Release Strategy](RELEASE.md) for details on our release cycles.*
