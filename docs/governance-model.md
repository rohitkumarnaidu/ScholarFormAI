# Governance Model

## Model: BDFL with Meritocratic Overlay

ScholarFormAI uses a **Benevolent Dictator for Life (BDFL)** model with strong meritocratic elements. The project lead has final authority on strategic decisions, but day-to-day governance is delegated to maintainers and working groups based on demonstrated expertise and contribution history.

This hybrid model balances:
- **Decisiveness** — the BDFL can break deadlocks
- **Community ownership** — maintainers and WGs drive most decisions
- **Meritocracy** — influence is earned through contribution quality

## Role Definitions

```
Project Lead (BDFL)
    └── Core Maintainers (3-5)
            └── Maintainers (10-20)
                    └── Contributors
                            └── Community Members
```

| Role | Responsibilities | Appointment | Voting Rights |
|------|-----------------|-------------|---------------|
| **Project Lead (BDFL)** | Final authority on project direction, appoints core maintainers, resolves deadlocks | Founder / succession | Veto power |
| **Core Maintainer** | Strategic decisions, RFC approval, WG oversight, release management | Appointed by lead | Yes (weighted) |
| **Maintainer** | Code review, issue triage, WG leadership, mentoring | Appointed by core maintainers | Yes |
| **Contributor** | Regular contributions, bug fixes, features, docs | Self-nominated + review | No (participate in discussion) |
| **Community Member** | Using the project, filing issues, discussions | Automatic | No |

## Decision Making Process

| Decision Type | Process | Who Decides |
|---------------|---------|-------------|
| Bug fix / minor change | Lazy consensus | Maintainer |
| New feature | RFC + lazy consensus | Core maintainers |
| Breaking change | RFC + vote | Core maintainers + lead |
| Governance change | RFC + supermajority vote | All maintainers |
| BDFL succession | RFC + unanimous vote | Core maintainers |

## Voting Procedures

| Term | Definition |
|------|------------|
| **Lazy consensus** | Silence implies agreement; 72-hour window |
| **Simple majority** | >50% of votes cast |
| **Supermajority** | >66% of votes cast |
| **Unanimous** | 100% of votes cast (abstentions excluded) |

- Voting is conducted via GitHub PR comments or a dedicated vote thread
- Voting period: 7 days for standard votes, 14 days for governance changes
- Abstentions are not counted toward the total

## Role Definitions

| Role | Description | Appointment | Revocation |
|------|-------------|-------------|------------|
| **Project Lead (BDFL)** | Final authority on project direction, appoints core maintainers, resolves deadlocks | Founder / succession by unanimous vote | N/A (voluntary) |
| **Core Maintainer** | Strategic decisions, RFC approval, release management, WG oversight | Appointed by lead | Lead vote + 30-day notice |
| **Maintainer** | Code review, issue triage, WG leadership, mentoring | Appointed by core maintainers | Core maintainer vote |
| **Contributor** | Regular contributions, bug fixes, features, docs | Self-nominated | Inactivity > 6 months |
| **Community Member** | Users, issue reporters, discussion participants | Automatic | N/A |

## Conflict Resolution

1. **Direct discussion** — parties discuss the issue in a public channel
2. **Mediation** — a neutral third-party mediator facilitates resolution
3. **Escalation to lead** — the project lead makes a binding decision
4. **Final appeal** — the lead's decision can be appealed to the core maintainers (requires 3/4 majority to override)

Conflicts involving the project lead are escalated to the core maintainers, who may vote to appoint an interim lead or call for a new lead election.
