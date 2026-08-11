<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: ScholarForm AI — Maintainers
description: Maintainer roles, responsibilities, and processes
sidebar_position: 1
version: "1.0"
status: ✅ Complete
owner: Project Lead
review_cadence: quarterly
last_updated: July 2026
---

# Maintainers

## Core Team

| Role | Name | Area | GitHub | Contact |
| ------ | ------ | ------ | -------- | --------- |
| **Project Lead (BDFL)** | Rohit Kumar Naidu | Overall direction, architecture, releases | [@rohitkumarnaidu](https://github.com/rohitkumarnaidu) | rohit@scholarform.ai |
| **Backend Lead** | _(open)_ | API design, pipeline, AI/ML services, database | — | — |
| **Frontend Lead** | _(open)_ | Next.js app, component library, design system | — | — |
| **DevOps Lead** | _(open)_ | CI/CD, deployment, monitoring, infrastructure | — | — |
| **AI/ML Engineer** | _(open)_ | LLM integration, RAG pipeline, model optimization | — | — |
| **Security Engineer** | _(open)_ | Auth, encryption, vulnerability management, compliance | — | — |
| **Docs Lead** | _(open)_ | Documentation, tutorials, API reference, changelog | — | — |

## Committers

| Name | Area | GitHub |
|------|------|--------|
| _(vacant)_ | — | — |

## Emeritus

Past maintainers who have stepped down but remain involved as advisors.

| Name | Former Role | GitHub |
|------|-------------|--------|
| _(none)_ | — | — |

## Role Responsibilities

### Project Lead

- Define product vision and roadmap
- Make final decisions on architecture, features, and releases
- Maintain project governance and CODEOWNERS
- Manage release process and versioning
- Resolve escalated conflicts

### Backend Lead

- Maintain and evolve API design (v1, v2, future versions)
- Oversee pipeline architecture (parsing, formatting, AI stages)
- Review all backend PRs within 48 hours
- Manage database schema, migrations, and performance
- Ensure test coverage stays above 70%

### Frontend Lead

- Maintain Next.js App Router architecture
- Oversee component library and design system
- Review all frontend PRs within 48 hours
- Ensure accessibility compliance (WCAG AA+)
- Manage frontend performance budgets

### DevOps Lead

- Maintain CI/CD pipelines (25+ GitHub Actions workflows)
- Manage Render, Vercel, and Supabase deployments
- Monitor production health and uptime
- Manage secrets, certificates, and infrastructure-as-code
- Conduct postmortems and incident reviews

### AI/ML Engineer

- Maintain LLM provider integration (10 providers)
- Optimize RAG pipeline (ChromaDB, embedding models)
- Tune prompts, temperature, and fallback strategies
- Monitor LLM costs and token usage
- Evaluate model quality and accuracy metrics

### Security Engineer

- Maintain authentication and authorization systems
- Manage encryption, key rotation, and secrets
- Conduct regular security audits and pen tests
- Maintain security headers, CSP, and CORS policies
- Respond to vulnerability disclosures

### Docs Lead

- Maintain all project documentation (docs/ directory)
- Write and update tutorials, guides, and API reference
- Ensure documentation accuracy and completeness
- Manage changelog and release notes
- Maintain cross-references between docs

## Becoming a Maintainer

### Nomination Process

1. **Contribution threshold** — 10+ substantial PRs merged over 3+ months
2. **Sponsorship** — Nominated by an existing maintainer
3. **Review period** — 2-week voting period among existing maintainers
4. **Vote** — Simple majority required; Project Lead has veto power
5. **Onboarding** — 1-month probationary period with mentorship

### Criteria for Nomination

- Consistent, high-quality contributions in the target area
- Understanding of the project's architecture and design philosophy
- Responsive to PR reviews and issues (within 72 hours)
- Positive and constructive communication style
- Alignment with project's code of conduct

### Responsibilities After Joining

- Review PRs within 48 hours (core business days)
- Triage new issues within 72 hours
- Participate in release coordination
- Maintain project documentation and CI/CD
- Mentor new contributors
- Attend monthly maintainer sync

## Review Rotation Schedule

Maintainers are assigned to review rotations weekly:

| Week | Backend Reviewer | Frontend Reviewer | Docs Reviewer |
| ------ | ------------------ | ------------------- | --------------- |
| 1 | Backend Lead | Frontend Lead | Docs Lead |
| 2 | Backend Lead | _(open)_ | _(open)_ |
| 3 | _(open)_ | Frontend Lead | Docs Lead |
| 4 | Backend Lead | Frontend Lead | _(open)_ |

- DevOps and Security reviews are on-demand for relevant PRs
- AI/ML reviews are on-demand for LLM/pipeline PRs
- If a reviewer is unavailable, ping the next person in rotation
- Rotating reviewer must respond within 24 hours or reassign

## Contact Channels

| Channel | Purpose | Access |
| --------- | --------- | -------- |
| **GitHub Issues** | Bug reports, feature requests, questions | [github.com/rohitkumarnaidu/ScholarFormAI/issues](https://github.com/rohitkumarnaidu/ScholarFormAI/issues) |
| **GitHub Discussions** | General discussion, Q&A, ideas | [github.com/rohitkumarnaidu/ScholarFormAI/discussions](https://github.com/rohitkumarnaidu/ScholarFormAI/discussions) |
| **Discord** | Real-time chat, maintainer coordination | Invite-only for maintainers; public channel for contributors |
| **Email** | Security disclosures, legal, press | security@scholarform.ai |

### Escalation Path

```
Issue filed → Triaged (72h) → Assigned to area lead →
  → Needs decision? → Project Lead
  → Needs infra change? → DevOps Lead
  → Security concern? → Security Engineer (PagerDuty)
```

## Related Documents

| Document | Description |
| ---------- | ------------- |
| [GOVERNANCE.md](../GOVERNANCE.md) | Full governance model and voting procedures |
| [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) | Community guidelines |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines |
| [CODE_REVIEW_STANDARDS.md](governance/CODE_REVIEW_STANDARDS.md) | PR review expectations |
| [DEVELOPER_ONBOARDING.md](developer-guide/DEVELOPER_ONBOARDING.md) | Onboarding new contributors |

---

*Last updated: July 2026*
