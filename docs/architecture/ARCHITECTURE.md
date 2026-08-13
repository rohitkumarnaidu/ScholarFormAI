# System Architecture

This document provides a high-level overview of the ScholarFormAI system architecture, detailing the interaction between the frontend, backend, AI models, and data persistence layers.

## High-Level Architecture Overview

ScholarFormAI employs a modern, decoupled architecture designed for high scalability, asynchronous processing, and real-time user feedback.

```mermaid
graph TD
    Client[Web Browser / CLI] --> API_GW(Next.js API Routes / Ingress)
    
    subgraph Frontend [Frontend Application]
        API_GW --> UI(Next.js App Router)
        UI --> State(Zustand / Context)
    end
    
    subgraph Backend [Backend Services]
        API_GW --> FastAPI(FastAPI App)
        FastAPI --> Celery[Celery Task Queue]
        FastAPI --> WS(WebSocket Server)
    end
    
    subgraph Storage [Data & Caching]
        FastAPI --> DB[(Supabase PostgreSQL)]
        Celery --> Redis[(Redis)]
        FastAPI --> Redis
        Celery --> Blob[(S3 / GCS Uploads)]
    end
    
    subgraph AI [AI Subsystem]
        Celery --> LLM(Groq / NVIDIA APIs)
        Celery --> VectorDB[(pgvector)]
    end
    
    UI <--> |Real-time Updates| WS
```

## Core Components

1. **Frontend (Next.js)**
   - Responsible for the UI, split-pane editor, and real-time preview.
   - Built using React and the App Router.

2. **Backend (FastAPI)**
   - Handles API requests, authentication, and routing.
   - Enqueues heavy document processing tasks to Celery.

3. **Task Queue (Celery + Redis)**
   - Manages asynchronous document formatting, PDF extraction, and AI generation tasks.

4. **Storage (Supabase + Blob Storage)**
   - Relational data and vector embeddings (pgvector) are stored in Supabase PostgreSQL.
   - Raw documents and formatted outputs are stored in object storage.

## Related Documents
- [System Design](SYSTEM_DESIGN.md)
- [Database Schema](../database/DATABASE.md)
- [AI Overview](../ai/AI.md)
