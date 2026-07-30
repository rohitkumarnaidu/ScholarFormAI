# AI Onboarding & Repository Map

This document is designed for AI Coding Assistants and LLMs to quickly grasp the context, structure, and architecture of the ScholarFormAI (AMF) repository.

## Project Purpose

ScholarFormAI automates the formatting of academic manuscripts using AI. It parses unstructured text, applies specific formatting guidelines (e.g., APA, MLA), manages references, and outputs compliant `.docx` files.

## Repository Map

### 1. Backend (`/backend/`)

The backend is a Python-based REST API (FastAPI) handling manuscript processing, AI orchestration, and database interactions.

- **`app/`**: Core application logic.
    - **`ai/`**: AI agents, prompt templates, and LLM integrations.
        - **`prompts/`**: Version-controlled prompt files used across agents.
        - **`rag/`**: Retrieval-Augmented Generation module utilizing Chroma DB for formatting rule lookups.
    - **`api/`**: FastAPI routers and endpoints.
    - **`services/`**: Core business logic.
    - **`models/`**: SQLAlchemy ORM models.
    - **`schemas/`**: Pydantic schemas for request/response validation.
- **`alembic/`**: Database migration scripts.

### 2. Frontend (`/frontend/`)

The frontend is built with React/Next.js and provides the web interface for users to upload manuscripts, review AI suggestions, and download formatted outputs.

### 3. CLI (`/cli/`)

A Python-based Command Line Interface allowing users to interact with ScholarFormAI directly from the terminal (e.g., `amf validate -i manuscript.md -s apa`).

### 4. Docs (`/docs/`)

Extensive documentation detailing architecture, API endpoints, deployment guides, and security protocols.

- **`AI_ARCHITECTURE.md`**: Deep dive into the AI features and models used.
- **`CHROMA_RAG_ARCHITECTURE.md`**: Details on the Vector Database and RAG pipeline.
- **`architecture/`**: System design diagrams and modular component overviews.

## LLM Interaction Guidelines

When working within this repository:

1. **Maintain Prompt Structures**: When editing files in `backend/app/ai/prompts/`, ensure backward compatibility and update version comments.
2. **Follow Type Hints**: Strict Python type hinting (Pydantic, Mypy) is enforced in the backend.
3. **Consult RAG documentation**: If modifying the formatting validation logic, ensure changes align with the RAG lookup mechanisms.
4. **Use Established Patterns**: When adding new AI agents, mimic the existing workflow definitions in the `ai/` module.
