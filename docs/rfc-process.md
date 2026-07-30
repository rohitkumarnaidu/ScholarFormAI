# RFC Process

## What is an RFC

An RFC (Request for Comments) is a design document that proposes a significant change to ScholarFormAI. RFCs are the primary mechanism for proposing, discussing, and deciding on major changes to the project. They ensure that decisions are documented, transparent, and informed by community input.

## When to Use an RFC

Use an RFC when the change is:

- **Architectural**: New subsystems, major refactors, database schema changes
- **API-breaking**: Changes to public APIs, webhook payloads, or SDK contracts
- **Cross-cutting**: Changes affecting multiple components or teams
- **Controversial**: Changes likely to spark debate or trade-offs
- **Costly**: Changes requiring significant implementation effort

Minor bug fixes, documentation typos, and routine dependency updates do not need an RFC.

## RFC Workflow

```
[Proposal] → [Discussion] → [Review] → [Decision] → [Implementation]
```

### 1. Proposal
- Fork the repo or create a branch
- Copy `RFC_TEMPLATE.md` to `docs/rfcs/YYYY-MM-DD-title.md`
- Fill out the template and open a Pull Request
- Label the PR with `rfc`

### 2. Discussion
- Comment period: minimum 7 days for minor RFCs, 14 days for major ones
- All community members may participate
- The author revises the RFC based on feedback
- Substantial changes reset the discussion timer

### 3. Review
- Core maintainers perform final review
- At least 2 maintainers must approve
- Review criteria: alignment with project goals, feasibility, maintenance cost, community impact

### 4. Decision
- **Accepted**: RFC is merged and enters implementation
- **Rejected**: RFC is closed with explanation
- **Deferred**: RFC is shelved for future reconsideration
- **Superseded**: A newer RFC replaces this one

### 5. Implementation
- Accepted RFCs are tracked in the project roadmap
- Implementation may be split across multiple PRs
- Each PR references the RFC in its description

## RFC Template

```markdown
# RFC-NNN: Title

- **Status:** [Draft | In Discussion | Accepted | Rejected | Deferred | Superseded]
- **Author:** Name
- **Date:** YYYY-MM-DD
- **PR:** #NNN

## Summary
One-paragraph summary of the proposal.

## Motivation
Why is this change needed? What problem does it solve?

## Design
Detailed technical design, including:
- Architecture diagrams or references
- API changes (if any)
- Data model changes (if any)
- Migration plan (if any)

## Drawbacks
Why should we not do this? Trade-offs and risks.

## Alternatives
What other approaches were considered and why were they rejected?

## Unresolved Questions
What questions remain to be resolved during implementation?
```

## Decision Records

Accepted RFCs become decision records. Each decision record is stored in `docs/decisions/` and includes:

- The final RFC with its decision status
- A summary of the discussion
- Voting results (if applicable)
- Implementation tracking links

Decision records are immutable once accepted. Amendments require a new RFC that supersedes the original.
