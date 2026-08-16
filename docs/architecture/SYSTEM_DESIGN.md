# System Design

This document details the complete end-to-end system design, asynchronous processing model, data flow, and core pipelines of ScholarForm AI.

## End-to-End Architecture

ScholarForm AI is designed to handle three computationally intensive workflows:

1. **Document Formatting:** Parsing unstructured DOCX/PDFs and applying journal-specific layout contracts.
2. **AI Agent Generation:** Synthesizing an academic manuscript from a prompt through an 11-step agentic pipeline.
3. **Multi-Doc Synthesis:** Combining multiple source PDFs into a single manuscript using RAG.

```mermaid
flowchart TB
    User((User / Researcher))
    
    subgraph Frontend [Next.js App Router]
        UI[Web UI]
        Preview[WYSIWYG Live Editor]
        State[Zustand / TanStack Query]
        UI <--> Preview
        UI <--> State
    end
    
    User -->|Upload / Prompt| UI
    
    subgraph API_Gateway [FastAPI Backend]
        AuthMiddleware[Auth Middleware<br>Supabase JWT]
        RateLimiter[Rate Limiting<br>SlowAPI + Redis]
        Router[API Routers<br>/api/v1/*]
        SSE[SSE / WebSockets<br>Real-time Status]
        
        AuthMiddleware --> RateLimiter --> Router
    end
    
    UI -->|REST API Calls| Router
    Router -.->|Server-Sent Events| UI
    Preview <.->|WebSockets| SSE
    
    subgraph Async_Workers [Celery Task Queue]
        FormatJob[Formatter Pipeline<br>12-Stage]
        GenJob[Generator Pipeline<br>11-Step Agent]
        SynthJob[Synthesis Pipeline<br>RAG-driven]
    end
    
    Router -->|Enqueue Job| Async_Workers
    Async_Workers -->|Publish Status| Redis
    Redis -->|Subscribe| SSE
    
    subgraph Data_Layer [Persistence & Caching]
        Supabase[(Supabase PostgreSQL<br>Users, Jobs, Audits)]
        BlobStorage[(Blob Storage<br>S3 / GCS)]
        ChromaDB[(ChromaDB<br>Guidelines & Chunks)]
        Redis[(Redis<br>Broker & Cache)]
    end
    
    Router <--> Supabase
    Router <--> BlobStorage
    Async_Workers <--> Supabase
    Async_Workers <--> BlobStorage
    Async_Workers <--> ChromaDB
    
    subgraph AI_Services [External AI / Parsing]
        LiteLLM[LiteLLM Router]
        Nvidia[NVIDIA NIM]
        Groq[Groq]
        Ollama[Ollama Local]
        Parsers[GROBID / Docling]
        
        LiteLLM --> Nvidia
        LiteLLM --> Groq
        LiteLLM --> Ollama
    end
    
    Async_Workers <--> LiteLLM
    Async_Workers <--> Parsers
```

## Core Workflows

### 1. Formatting Workflow

When a user uploads a document to be formatted:

1. **Ingestion:** File uploaded to Supabase Blob Storage; Job created in PostgreSQL.
2. **Parsing:** Fallback chain parses document (GROBID -> Docling -> PyMuPDF).
3. **Structuring:** Content is converted to an internal Abstract Syntax Tree (AST).
4. **Validation:** Checks against `contract.yaml` (Jinja2 specs).
5. **Formatting:** Jinja2 compiler renders the final layout according to publisher constraints (IEEE, APA, Springer).

### 2. Generation Workflow (AI Agent)

When a user provides a prompt:

1. **Planning:** LLM maps out a research structure.
2. **Drafting:** Agent generates content section-by-section.
3. **Review:** Internal critic agent reviews output.
4. **Compilation:** Output is converted to DOCX/PDF via the formatting engine.

### 3. Synthesis Workflow

When multiple PDFs are provided:

1. **Chunking & Embedding:** PDFs chunked and stored in ChromaDB.
2. **Retrieval:** RAG queries context based on topic.
3. **Synthesis:** LLM synthesizes common themes into a cohesive manuscript.

## Scalability and Reliability

- **Stateless Backend:** FastAPI instances hold no state. RAG relies on ChromaDB; Queues on Redis.
- **Circuit Breakers & Fallbacks:** AI LLM calls fallback (Nvidia -> Groq -> Ollama) to prevent timeouts. Parser calls also fallback gracefully.
- **Asynchronous Feedback:** User receives real-time progress via Redis Pub/Sub connected to Server-Sent Events (SSE), preventing HTTP timeouts for long jobs.

## Related Documents

- [Database Schema](../database/DATABASE.md)
- [Realtime Architecture](REALTIME_ARCHITECTURE.md)
- [Security Architecture](SECURITY_ARCHITECTURE.md)
