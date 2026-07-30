<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI Governance

## Project Stewardship Model

ScholarForm AI uses a **BDFL + Core Team** governance model, designed to balance rapid development velocity with community participation and long-term project health.

## Roles

### Benevolent Dictator for Life (BDFL)

The BDFL has final authority on all project decisions, including technical direction, feature acceptance, and conflict resolution.

- **Current BDFL:** Rohit Kumar Naidu
- **Scope:** API design decisions, breaking changes, strategic roadmap
- **Limits:** The BDFL cannot unilaterally change this governance document or the project license without Core Team approval.

### Core Team

Core Team members are trusted contributors who have demonstrated sustained, high-quality contribution to the project. Responsibilities include:

- Reviewing and merging pull requests
- Triaging and responding to issues
- Guiding technical discussions and RFCs
- Mentoring new contributors
- Voting on governance changes and new Core Team members

Core Team membership is granted by a ⅔ majority vote of the existing Core Team, with the BDFL holding veto power.

### Committers

Committers have write access to the repository but are not part of the Core Team. They are expected to:

- Self-review their own code (with Core Team oversight)
- Participate in code reviews
- Follow project conventions and style guides

Committer status is granted by any Core Team member via a lazy-consensus process (7-day objection period).

### Contributors

Anyone who submits a pull request, files a bug report, improves documentation, or participates in discussions is a contributor. No formal status required.

## Decision-Making

| Type | Process | Approver |
|------|---------|----------|
| Bug fixes, minor features | Standard PR review | 1 Core Team approval |
| Major features | RFC + PR review | 2 Core Team approvals |
| Breaking API changes | RFC + 2-week comment period | Core Team majority |
| Governance changes | RFC + 4-week comment period | Core Team ⅔ majority + BDFL |
| New Core Team members | Nomination + vote | Core Team ⅔ majority |
| License changes | Community vote | Consensus |

## Code of Conduct

All interactions in ScholarForm AI spaces are governed by the [Code of Conduct](code-of-conduct.md). Violations should be reported to the Core Team.

## Conflict Resolution

Disagreements within the project should be escalated through these steps:

1. Direct discussion between involved parties (on the PR/issue)
2. Mediation by a Core Team member
3. Core Team vote (simple majority)
4. BDFL final ruling
