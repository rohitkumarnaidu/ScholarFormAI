<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: "ADR 011: Per-Section Equation Numbering"
description: Switch from global flat equation numbering to per-section hierarchical numbering
sidebar_position: 38
version: "1.0"
status: ✅ Accepted
owner: Engineering Team
review_cadence: never
last_updated: July 2026
---

# ADR 011: Per-Section Equation Numbering

## Context

The `NumberingEngine` (`backend/app/pipeline/formatting/numbering.py`) currently applies global flat equation numbering (Eq. 1, Eq. 2, …) regardless of document structure. Multi-chapter manuscripts submitted through the generator and synthesis pipelines require section-scoped hierarchical numbering (Eq. 2.1, Eq. 2.2, …) to meet publisher submission guidelines (IEEE, Springer LNCS, Elsevier).

The existing `contract.yaml` schema already has an `equations.scope` key whose only supported value is `"global"`. Templates that declare hierarchical numbering in their contract have no way to opt into per-section numbering, and the cross-reference engine has no logic for resolving dotted equation numbers.

## Decision

Extend `NumberingEngine.apply_numbering` to support a `scope: per_section | global` option, defaulting to `per_section` for templates whose contract declares hierarchical heading numbering:

- **Scope detection**: Read `equations.scope` from the loaded contract. If absent or `"global"`, preserve today's flat numbering. If `"per_section"`, reset the equation counter at each top-level section (`BlockType.heading_1`) and emit `{section}.{index}` as the equation number.
- **Bracket preservation**: The existing `equations.brackets` setting (`()`, `[]`, or none) applies identically to per-section numbers (e.g., `(2.1)` or `[2.1]`).
- **Cross-reference awareness**: The `CrossReferenceEngine` must parse dotted equation numbers when building `ref` fields in generated documents. Period characters in numbers must not be treated as sentence boundaries during backlink resolution or docstring reference extraction.

## Consequences

- **NumberingEngine** — A new `_apply_per_section_equation_numbering` method will walk document sections, tracking equation indices per section. A separate `_is_per_section_template` helper checks the contract flag.
- **CrossReferenceEngine** — The regex patterns used to extract `@ref` backlinks and `ref` targets must be updated to accept dotted identifiers (e.g., `(2.1)`). In `backend/app/pipeline/formatting/cross_reference.py`, the pattern `r'\((\d+)\)'` becomes `r'\((\d+(?:\.\d+)*)\)'`.
- **Default behavior** — Existing templates without an explicit `equations.scope` in their contract continue to use global numbering, maintaining backward compatibility.
- **Migration** — No data migration required; numbering is computed at format-time, not stored.
- **Template authors** — Must set `equations.scope: per_section` in `contract.yaml` to opt in. The IEEE and Springer LNCS templates will be updated as part of this ADR.

## Compliance

This decision has been implemented and is verified by:

- `backend/tests/test_numbering.py` — `NumberingEngine.apply_numbering()` per-section scope
- `backend/tests/test_equation_standardizer.py` — equation bracket and scope handling
- `backend/tests/pipeline/test_equations.py` — pipeline integration with per-section numbering
- `backend/tests/pipeline/test_equations_deep.py` — edge cases (single section, cross-section refs)
- `backend/tests/pipeline/test_equation_standardizer_deep.py` — standardizer edge cases
- `backend/tests/pipeline/test_enhanced_numbering.py` — hierarchical numbering with dotted identifiers
- `backend/app/pipeline/formatting/numbering.py` — `_apply_per_section_equation_numbering()` method
- `backend/app/pipeline/formatting/cross_reference.py` — dotted identifier regex `r'\((\d+(?:\.\d+)*)\)'`

**See also:**

- [NumberingEngine](../../backend/app/pipeline/formatting/numbering.py) — source implementation
- [CrossReferenceEngine](backend/app/pipeline/formatting/cross_reference.py) — dotted identifier support
- [ADR 009: Template Contract System](009-template-contract-system.md) — `equations.scope` contract key
- [IEEE Template Contract](../../backend/app/templates/ieee/contract.yaml) — per-section enabled template
