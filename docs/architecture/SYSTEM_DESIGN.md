# System Design

This document details the detailed system design, asynchronous processing model, and data flow of ScholarFormAI.

## Document Processing Flow

The core workflow of ScholarFormAI involves processing raw documents into publisher-ready formats. Because these tasks are computationally and AI-intensive, they are handled asynchronously.

```mermaid
sequenceDiagram
    participant User
    participant NextJS as Frontend (Next.js)
    participant FastAPI as Backend (FastAPI)
    participant Celery as Worker (Celery)
    participant AI as AI Agents
    
    User->>NextJS: Upload Document & Select Template
    NextJS->>FastAPI: POST /api/v1/format
    FastAPI->>FastAPI: Validate & Save to Storage
    FastAPI->>Celery: Enqueue Formatting Task
    FastAPI-->>NextJS: 202 Accepted (Task ID)
    NextJS->>User: Show Loading State
    
    loop Real-time Polling / WS
        NextJS->>FastAPI: Subscribe to Task Status
        Celery->>FastAPI: Update Task Status (Redis)
        FastAPI-->>NextJS: Status Updates (SSE/WS)
    end
    
    Celery->>AI: Trigger Layout & Synthesis Agents
    AI-->>Celery: Formatted Content
    Celery->>Celery: Generate Output File (PDF/DOCX)
    Celery->>Redis: Mark Task Complete
    
    FastAPI-->>NextJS: Task Complete + Download URL
    NextJS->>User: Render Split-Pane Preview
```

## Scalability and Reliability

- **Stateless Backend:** The FastAPI application instances are entirely stateless, allowing horizontal scaling behind a load balancer.
- **Queue Backpressure:** Celery is configured with rate limits to prevent overwhelming the downstream LLM APIs (Groq/NVIDIA).
- **Fault Tolerance:** Failed tasks are automatically retried with exponential backoff.

## Related Documents
- [Architecture](ARCHITECTURE.md)
- [Agents](../ai/AGENTS.md)
