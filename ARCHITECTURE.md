# Architecture

## System Overview

AMF follows a microservices-inspired architecture with clear separation between API, formatting engine, frontend, and tooling.

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Web UI   │  │ CLI      │  │ SDK      │  │ API      │   │
│  │ (React)  │  │ (Click)  │  │ (Python) │  │ (curl)   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │             │              │         │
└───────┼──────────────┼─────────────┼──────────────┼─────────┘
        │              │             │              │
        ▼              ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              FastAPI Application                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │   │
│  │  │ Routes  │  │ Models  │  │ Middleware│              │   │
│  │  └────┬────┘  └─────────┘  └─────────┘               │   │
│  └───────┼──────────────────────────────────────────────┘   │
└──────────┼──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Formatter │  │  Parser  │  │Validator │  │  Style   │   │
│  │ Service  │  │  Service │  │ Service  │  │ Registry │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │             │              │         │
└───────┼──────────────┼─────────────┼──────────────┼─────────┘
        │              │             │              │
        ▼              ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Manuscript│  │  Section │  │Reference │  │  Author  │   │
│  │  Schema  │  │  Schema  │  │  Schema  │  │  Schema  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### Backend (FastAPI)

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **DOCX Generation**: python-docx
- **Validation**: Pydantic v2
- **Config**: pydantic-settings

The backend exposes a RESTful API and contains all business logic for parsing, validating, and formatting manuscripts.

### Frontend (Next.js)

- **Framework**: Next.js 14 with App Router
- **Styling**: Tailwind CSS
- **Components**: Custom UI components with Radix UI primitives
- **State**: React hooks and server components

### CLI (Click)

- **Framework**: Click
- **Output**: Rich (terminal formatting)
- **Config**: JSON-based configuration

### SDK (Python)

- **HTTP**: httpx (sync + async)
- **Models**: Pydantic v2
- **Error handling**: Custom exception hierarchy

## Data Flow

1. User submits manuscript text + style + options via UI/CLI/API
2. Parser service converts raw text into structured Manuscript model
3. Validator checks structure and style compliance
4. Formatter generates DOCX using python-docx with style-specific formatting
5. Response includes download URL, page count, and metadata

## Key Design Decisions

- **Stateless API**: No user session state. Each request is self-contained.
- **Temporary files**: Formatted documents are stored temporarily for download.
- **Local-first**: CLI can work without API server (with optional dependencies).
- **Style registry**: Built-in styles are registered at startup. Custom styles can be added programmatically.
