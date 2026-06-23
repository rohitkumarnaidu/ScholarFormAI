<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Branch Protection Settings
description: GitHub branch protection rules for main and develop branches
sidebar_position: 6
version: "1.0"
status: ✅ Complete
owner: DevOps Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Branch Protection Settings

Apply these settings in GitHub for the `main` branch.

## Required Status Checks
- `backend-ci`
- `frontend-ci`
- `security`

## Rules
- Require pull request reviews before merging.
- Require status checks to pass before merging.
- Disallow direct pushes to `main`.
