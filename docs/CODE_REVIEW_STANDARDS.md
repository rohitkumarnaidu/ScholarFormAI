<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Code Review Standards

## Overview

Code review is a cornerstone of quality and secure coding practices at ScholarForm AI. Every change must be reviewed before merging to `main`. This document defines how code review is conducted, what must be checked, and what is required for acceptance.

## Review Requirements

### Who Can Review

- Pull requests require approval from at least one Core Team member.
- Committers may perform initial reviews but final approval must come from a Core Team member.
- The PR author must NOT be the sole approver.

### Review Timeline

| Priority | Response Target |
| ---------- | ---------------- |
| Security fixes | 4 hours |
| Critical bug fixes | 24 hours |
| Standard PRs | 48 hours (business days) |

## What Reviewers Must Check

### Correctness

- Does the code do what it claims?
- Are edge cases handled?
- Are error paths properly managed?

### Test Coverage

- Are new features accompanied by tests?
- Do all existing tests still pass?
- Is coverage maintained above 70% (backend) and passing (frontend)?

### Security

- Are inputs validated and sanitized?
- Are there any hardcoded credentials or secrets?
- Does the change follow the principle of least privilege?
- Are there any SQL injection, XSS, or command injection vectors?
- Are authentication and authorization checks in place for protected routes?

### Style & Standards

- Python: Does the code pass `ruff check` and mypy?
- Frontend: Does the code pass ESLint with `--max-warnings 0`?
- Are type annotations present for all public APIs?
- Does the code follow the project's coding conventions?

### Documentation

- Are public APIs documented?
- Are changes reflected in relevant docs?
- Is a CHANGELOG entry included?

### Performance

- Are there obvious performance regressions?
- Are database queries optimized (N+1 queries, missing indexes)?

## Review Process

1. **Author** opens PR against `main` with completed checklist.
2. **CI** runs automatically — backend-ci, frontend-ci, security scans, dependency review.
3. **Reviewer** is assigned or self-assigns.
4. **Review** covers the checklist above. Comments are left inline.
5. **Author** addresses feedback with additional commits.
6. **Reviewer** re-reviews and either approves or requests further changes.
7. **Merge** is performed by the reviewer or author (once approved) using squash merge.

## What Constitutes Acceptance

A PR is accepted when:

- At least one Core Team member has approved.
- All CI checks pass.
- No security issues are introduced.
- Test coverage requirements are met.
- The DCO check passes (all commits signed off).

## Blocking Criteria

A PR MUST be rejected or held if:

- It introduces a security vulnerability.
- It reduces test coverage without justification.
- It contains hardcoded secrets or credentials.
- CI checks fail.
- Commits are not signed off (DCO).
- The change breaks existing functionality.

## Metrics

We track the following code review metrics:

- **Review coverage**: Percentage of PRs receiving at least one review (target: 100%).
- **Time to first review**: Median time from PR open to first review comment (target: <24h).
- **Merge time**: Median time from PR open to merge (target: <72h).

---

*Last updated: July 2026*
