---
title: ScholarForm AI — OpenCode Skills
description: Reusable skill definitions for AI-assisted ScholarForm AI workflows
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Engineering
review_cadence: quarterly
last_updated: June 2026
---

# OpenCode Skills

This directory defines reusable skills that provide specialized instructions and workflows for OpenCode agents.

## Available Skills

| Skill | Description |
|-------|-------------|
| [Code Review](code-review.md) | PR review workflow with per-stack checklist |
| [Pipeline Debug](pipeline-debug.md) | Systematic debugging for document processing pipeline |
| [API Design](api-design.md) | Standards for designing new REST endpoints under `/api/v1/` |
| [Migration](migration.md) | Workflow for creating and applying Alembic database migrations |
| [Release](release.md) | Step-by-step release process from version bump to deployment |

## Skill Format

```yaml
name: Skill Name
description: One-line description
trigger: When to invoke this skill
workflow: |
  Step-by-step instructions for the agent to follow.
```

## See Also

- [Agents](../agents/README.md) — Agent definitions that use these skills
- [Architecture Overview](content/Architecture Overview/Architecture Overview.md)
