# Governance Model

This document describes the governance model for the **ScholarForm AI** open-source project. Our goal is to ensure the project remains sustainable, transparent, and community-driven while maintaining enterprise-grade standards.

## 1. Project Structure

### 1.1 The Steering Committee

The Steering Committee is the primary decision-making body for ScholarForm AI. It is responsible for:

- Approving the project [Roadmap](ROADMAP.md).
- Resolving technical disputes.
- Overseeing the [Code of Conduct](CODE_OF_CONDUCT.md).
- Managing project assets, trademark considerations, and overall Open Source Program Office (OSPO) alignment.

Currently, the Steering Committee consists of the Core Maintainers listed in [MAINTAINERS.md](MAINTAINERS.md).

### 1.2 Maintainers

Maintainers manage the day-to-day operations: reviewing code, triaging issues, and mentoring contributors. Maintainers have commit access to the core repositories.

### 1.3 Contributors

Anyone who interacts with the project—whether by submitting code, writing documentation, reporting bugs, or helping others—is a contributor.

## 2. Decision Making Process

We operate on a model of **Lazy Consensus**.

- When a proposal is made (e.g., via a GitHub Issue, PR, or Request for Comments (RFC)), it is assumed approved if no maintainer objects within 72 hours.
- If an objection is raised, the maintainers will attempt to resolve it through discussion.
- If consensus cannot be reached, the Steering Committee will call for a vote. A simple majority among the Steering Committee is required to pass a binding decision.

## 3. RFC (Request for Comments)

For major architectural changes—such as introducing new Agentic AI paradigms, altering the core PDF extraction pipeline, or changing the database schema—an RFC must be submitted.

- RFCs are submitted as PRs to an `rfcs/` directory (or via detailed GitHub Discussions).
- They must outline the motivation, technical design, alternatives considered, and backward compatibility implications.

## 4. Modifications to Governance

This governance model is a living document. Changes to this model can be proposed by any contributor but must be ratified by a two-thirds majority of the Steering Committee.

For more information, please see our [Contributing Guidelines](CONTRIBUTING.md).
