<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# ScholarForm AI Examples

This directory contains working examples to help you get started with ScholarForm AI.

## Available Examples

| Example | Description | Tech |
|---------|-------------|------|
| [quick-format](quick-format/README.md) | Format a manuscript with one command | Python CLI |
| [custom-template](custom-template/README.md) | Create and use a custom template | Python, Jinja2 |
| [api-scripts](api-scripts/README.md) | ScholarForm API client examples | Python, JavaScript |

## Running Examples

Each example has its own README with setup instructions. Most require:

1. A running ScholarForm backend (local or remote)
2. Python 3.12 and the packages from `backend/requirements.txt`

```bash
# Quick-start any example
cd examples/quick-format
python format_paper.py --template ieee --input my-paper.docx
```
