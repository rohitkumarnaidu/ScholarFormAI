<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


# Custom Template Example

Create and register a custom journal template for ScholarForm.

## Structure

A template consists of three files in a folder under `backend/app/templates/`:

```
backend/app/templates/my-journal/
├── template.docx       # DOCX with Jinja2 placeholders
├── contract.yaml       # Variable declarations and validation
└── styles.csl          # Citation style (optional, defaults to APA)
```

## Quick Start

```bash
# 1. Create template directory
mkdir backend/app/templates/my-journal

# 2. Copy an existing template as starting point
cp backend/app/templates/ieee/template.docx backend/app/templates/my-journal/

# 3. Create contract.yaml
cat > backend/app/templates/my-journal/contract.yaml << 'EOF'
name: "My Journal"
description: "Custom journal template"
variables:
  title:
    type: string
    required: true
    description: "Paper title"
  authors:
    type: list
    required: true
    description: "List of authors"
    items:
      type: object
      properties:
        name:
          type: string
          required: true
        affiliation:
          type: string
          default: ""
  abstract:
    type: string
    required: false
  sections:
    type: list
    required: true
    items:
      type: object
      properties:
        heading:
          type: string
          required: true
        content:
          type: string
          required: true
EOF

# 4. Restart backend (new templates auto-discovered on startup)
```

## Contract Reference

See [Template Creation Guide](../../docs/template_creation.md) for full contract schema documentation.
