<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: Benchmarking Template Compliance in ScholarForm AI
authors:
  - Asha Verma
  - Daniel Wu
affiliations:
  - ScholarForm Research Lab
keywords:
  - formatting
  - benchmarking
  - academic writing
---
# Abstract
This benchmark measures whether the IEEE formatter preserves structure, references, and hyperlinks.

# Introduction
The workflow should preserve links such as [ScholarForm AI](https://scholarform.ai) while keeping a stable heading hierarchy.[^1]

## Methods
We compare rendered output against structural goldens instead of pixel-perfect snapshots.

# Results
The current formatter maintains titles, sections, and reference ordering consistently enough for a structural baseline.

# Conclusion
Golden-file checks give us a measurable baseline before renderer fixes land.

# References
[1] A. Verma and D. Wu, "Template Benchmarks for Manuscript Tooling," 2025.
[2] J. Chen, "Structural Validation for DOCX Pipelines," 2024.

[^1]: Structural benchmarks stay robust even when template spacing changes.
