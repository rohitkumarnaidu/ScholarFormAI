<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Quick Format Example

Format a DOCX manuscript against any journal template with a single CLI command.

## Usage

```bash
# Install dependencies
pip install requests

# Run the formatter
python format_paper.py --template ieee --input paper.docx --output formatted.docx
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--template` | `ieee` | Template name (acm, apa, chicago, elsevier, harvard, ieee, mla, modern_blue, modern_gold, modern_red, nature, none, numeric, portfolio, resume, springer, vancouver) |
| `--input` | — | Path to input DOCX file |
| `--output` | `formatted.docx` | Path for formatted output |
| `--api-url` | `http://localhost:8000` | ScholarForm API base URL |
| `--api-key` | — | API key (optional, for authenticated features) |

## Example

```bash
python format_paper.py --template springer --input manuscript.docx --output springer-ready.docx
```

## Files

- `format_paper.py` — The CLI script
