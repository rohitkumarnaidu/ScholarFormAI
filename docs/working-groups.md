# Working Groups

## Purpose

Working groups (WGs) are semi-autonomous teams focused on specific areas of ScholarFormAI. They enable parallel development, deep expertise, and community ownership of different parts of the project.

Each working group:
- Owns a specific domain (code, docs, community)
- Makes decisions within its scope
- Reports progress to the broader project
- Maintains its own roadmap and backlog

## Current Working Groups

| Working Group | Scope | Lead | Meeting |
|---------------|-------|------|---------|
| **Backend** | API server, database, task queue, storage | TBD | Bi-weekly |
| **Frontend** | Web UI, client SDKs, accessibility | TBD | Bi-weekly |
| **AI/ML** | LLM integration, prompt engineering, RAG pipeline | TBD | Weekly |
| **Infrastructure** | CI/CD, Docker, deployment, monitoring, security | TBD | Bi-weekly |
| **Security** | Vulnerability management, audits, compliance, cryptography | TBD | Monthly |
| **Documentation** | User docs, API reference, guides, translations | TBD | Monthly |

## How to Join a Working Group

1. Express interest in the relevant GitHub Discussion or issue
2. Attend two consecutive meetings as a guest
3. A current member sponsors your membership
4. You are added to the WG roster and meeting invitations

## How to Start a New Working Group

1. Post an RFC in `docs/rfcs/` proposing the new WG
2. Gather at least 3 initial members
3. Define the WG charter (scope, goals, deliverables)
4. Get approval from the project lead
5. Announce on GitHub Discussions

## Meeting Cadence

| WG | Frequency | Duration | Format |
|----|-----------|----------|--------|
| Backend | Bi-weekly | 45 min | Async + sync |
| Frontend | Bi-weekly | 45 min | Async + sync |
| AI/ML | Weekly | 60 min | Sync |
| Infrastructure | Bi-weekly | 45 min | Async + sync |
| Security | Monthly | 60 min | Sync |
| Documentation | Monthly | 30 min | Async |

Meeting notes are published in `docs/working-groups/meeting-notes/` after each session.

## Decision Making Within Groups

- Working groups use **lazy consensus**: silence implies agreement
- Decisions affecting multiple WGs require cross-WG review
- Stalled decisions escalate to the project lead after 14 days
- Each WG maintains a decision log in `docs/working-groups/decisions/`
