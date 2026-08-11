<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

---

title: Guide — Creating a Custom Template
description: How-to guide for building and registering custom journal templates
sidebar_position: 2
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: July 2026
---

# Guide: Creating a Custom Template

This guide walks through creating a custom journal template for ScholarForm.

## Template Structure

Each template lives in its own folder under `backend/app/templates/`:

```
backend/app/templates/my-journal/
├── template.docx       # Required: DOCX with Jinja2 placeholders
├── contract.yaml       # Required: Variable declarations
└── styles.csl          # Optional: Citation style
```

## Step 1: Create the Folder

```bash
mkdir backend/app/templates/my-journal
```

## Step 2: Prepare Template DOCX

Start from an existing template:

```bash
cp backend/app/templates/ieee/template.docx backend/app/templates/my-journal/
```

Open `template.docx` in Word or LibreOffice. Insert Jinja2 placeholders where content should appear:

```
{{ title }}
{{ abstract }}
{{ authors[0].name }}
{% for section in sections %}
  {{ section.heading }}
  {{ section.content }}
{% endfor %}
```

## Step 3: Write the Contract

Create `backend/app/templates/my-journal/contract.yaml`:

```yaml
name: "My Journal"
description: "Template for My Journal submissions"
version: "1.0"
variables:
  title:
    type: string
    required: true
    description: "Paper title"
  authors:
    type: list
    required: true
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
  keywords:
    type: list
    required: false
    items:
      type: string
```

## Step 4: Add Citation Style (Optional)

Download a CSL file from the [CSL Repository](https://github.com/citation-style-language/styles):

```bash
curl -o backend/app/templates/my-journal/styles.csl \
  https://raw.githubusercontent.com/citation-style-language/styles/master/ieee.csl
```

If no `styles.csl` is provided, APA is used by default.

## Step 5: Restart & Verify

```bash
# Backend auto-discovers new templates on startup
# The template appears as "my-journal" in the API
curl http://localhost:8000/api/v1/templates
```

## Step 6: Test Your Template

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@paper.docx" \
  -F "template=my-journal"
```

## Template Contract Reference

See the [Template Creation Guide](../user-guide/template_creation.md) for the full contract schema.

## Best Practices

1. **Validate early** — Test your template with a simple document first
2. **Use default values** — Set `default:` in contract.yaml for optional fields
3. **Keep it focused** — One template = one journal. Don't make multi-purpose templates
4. **Test all citation styles** — If you include a CSL, test with 1, 5, and 20+ references
5. **Version your templates** — Use the `version` field in contract.yaml
