---
title: ScholarForm AI — OpenCode Agents
description: Specialized AI agent personas for ScholarForm AI development workflows
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Engineering
review_cadence: quarterly
last_updated: June 2026
---

# OpenCode Agents

This directory defines specialized AI agent personas for OpenCode-assisted ScholarForm AI development. Each agent has a distinct role, expertise area, and toolset.

## Available Agents

| Agent | Role | Expertise |
|-------|------|-----------|
| [Architect](architect.md) | System Architect | Architecture decisions, data flow, pipeline design |
| [Backend Dev](backend-dev.md) | Python/FastAPI Developer | API routes, services, DB, Celery, middleware |
| [Frontend Dev](frontend-dev.md) | Next.js/React Developer | Components, state, real-time features, styling |
| [ML Engineer](ml-engineer.md) | AI/ML Engineer | LLM integration, RAG, SciBERT, model management |
| [DevOps](devops.md) | DevOps Engineer | CI/CD, Docker, Render, monitoring, security |
| [QA](qa.md) | QA Engineer | Testing strategy, Playwright, pytest, contract tests |

## Agent Interaction Model

```mermaid
graph TB
    subgraph "Developer"
        DEV["Developer Request"]
    end
    subgraph "OpenCode Agents"
        ARCH["Architect<br/>System design"]
        BE["Backend Dev<br/>API + services"]
        FE["Frontend Dev<br/>UI + components"]
        ML["ML Engineer<br/>LLM + RAG"]
        OPS["DevOps<br/>CI/CD + infra"]
        QA["QA Engineer<br/>Tests + quality"]
    end
    subgraph "Codebase"
        CODE["ScholarForm AI<br/>Backend + Frontend + Docs"]
    end
    DEV --> ARCH
    DEV --> BE
    DEV --> FE
    DEV --> ML
    DEV --> OPS
    DEV --> QA
    ARCH --> CODE
    BE --> CODE
    FE --> CODE
    ML --> CODE
    OPS --> CODE
    QA --> CODE
```

## Agent Format

```yaml
name: Agent Name
role: Role description
model: Preferred model
instructions: |
  System prompt defining behavior, constraints, and preferences.
capabilities:
  - Capability description
```

## See Also

- [Skills](../skills/README.md) — Companion skill definitions
- [Architecture Overview](content/Architecture Overview/Architecture Overview.md)
