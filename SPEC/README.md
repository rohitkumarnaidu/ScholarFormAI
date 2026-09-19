<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# ScholarForm AI — System Specifications (`SPEC/`)

> **AUTHORITATIVE & NORMATIVE REPOSITORY SPECIFICATIONS**  
> Every document under `SPEC/` defines an enforceable requirement, architecture decision, interface contract, data schema, or operational invariant for the ScholarForm AI platform.  
> Code contributions and pull requests MUST strictly adhere to these specifications. Any discrepancy between codebase behavior and `SPEC/` represents either an implementation bug or an unapproved specification deviation.

---

## 1. Specification Taxonomy

The `SPEC/` tree is partitioned into domain-specific contract registries:

| Domain | Directory | Scope & Authority |
| :--- | :--- | :--- |
| **Requirements** | [`SPEC/requirements/`](requirements/) | Comprehensive FRS, SRS, PRD, and core system capabilities. |
| **Architecture** | [`SPEC/architecture/`](architecture/) | Accepted Architectural Decision Records (ADRs) and system invariants. |
| **API Contracts** | [`SPEC/api/`](api/) | JSON response envelopes, machine error catalogs, endpoint schemas, and tier SLAs. |
| **Data Contracts** | [`SPEC/data/`](data/) | PostgreSQL schemas, Supabase Row-Level Security (RLS), and DOCX template AST rules. |
| **AI & Agents** | [`SPEC/ai/`](ai/) | Generator Mode B 11-step agent protocol, 4-tier LLM fallback hierarchy, and RAG invariants. |
| **Pipeline** | [`SPEC/pipeline/`](pipeline/) | Document formatting pipeline stages, state transitions, and execution contracts. |
| **Governance** | [`SPEC/governance/`](governance/) | Enforced Monorepo Coding Standards, PR review gates, and Branch Protection rules. |
| **Operations** | [`SPEC/operations/`](operations/) | Service Level Objectives (SLOs), SLA commitments, and Feature Flag registries. |
| **Security** | [`SPEC/security/`](security/) | Threat model boundaries, zero-trust requirements, and compliance obligations. |
| **Testing** | [`SPEC/testing/`](testing/) | Verification gates, test coverage criteria, and acceptance thresholds. |

---

## 2. Distinction from `docs/`

- **`SPEC/` (Authoritative Contracts):** Implementation-facing, machine/developer-binding, normative requirements. Does not contain tutorials, promotional summaries, or narrative walkthroughs.
- **`docs/` (Human-Facing Documentation):** Developer onboarding, user guides, architecture explanations, operational runbooks, tutorials, API quickstarts, and community resources.

---

## 3. RFC & Modification Process

Specifications are version-controlled alongside the codebase. To propose a change to any document in `SPEC/`:

1. Open an RFC issue describing the architectural or contract motivation.
2. Submit a Pull Request modifying the specific contract in `SPEC/` alongside the implementing code changes.
3. Obtain approval from the BDFL / Core Architecture team as defined in [`SPEC/governance/CODE_REVIEW_STANDARDS.md`](governance/CODE_REVIEW_STANDARDS.md).
