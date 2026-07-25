# Architecture Overview

## System Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Web Interface     │────▶│    REST API      │────▶│  Formatting     │
│   (Next.js)         │     │    (FastAPI)      │     │  Engine         │
└─────────────────────┘     └──────────────────┘     └─────────────────┘
         │                          │                         │
         ▼                          ▼                         ▼
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   CLI Tool          │     │   Parser         │     │  Style Registry │
│   (Click + Rich)    │     │   Service        │     │  9 Built-in     │
└─────────────────────┘     └──────────────────┘     └─────────────────┘
         │                          │                         │
         ▼                          ▼                         ▼
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Python SDK        │     │  Validator       │     │  python-docx    │
│   (httpx)           │     │  Service         │     │  (DOCX Gen)     │
└─────────────────────┘     └──────────────────┘     └─────────────────┘
```

## Components

### Backend (FastAPI)
Python-based REST API providing formatting, validation, and preview endpoints.

### Frontend (Next.js)
Modern React-based web interface for interactive manuscript formatting.

### CLI (Click)
Terminal-based tool for scripting and automation.

### SDK (Python)
Client library for Python applications.
