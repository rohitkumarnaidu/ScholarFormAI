<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: "ADR 009: Template Contract Validation System"
description: Decision to use contract.yaml for template variable validation
sidebar_position: 48
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 009: Template Contract Validation System

## Context

Templates must be validated before use to ensure they produce predictable output. Without validation, malformed templates cause confusing rendering failures.

## Decision

Each template folder may include a `contract.yaml` file that declares:

- Required Jinja variables
- Supported options (cover_page, toc, page_numbers)
- Output constraints (max page count, required sections)

The pipeline validates documents against the contract before rendering.

## Consequences

- Early failure with clear error messages when template requirements are unmet
- Templates without a contract still work (backward compatible)
- Contract schema defined in `backend/app/pipeline/contract_schema.py`
- New templates should include a contract for production use
