<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->


---
title: ScholarForm AI — Template Creation Tutorial
description: How to create, test, and deploy manuscript templates with contract.yaml
sidebar_position: 11
version: "1.0"
status: ✅ Complete
owner: Docs Team
review_cadence: quarterly
last_updated: June 2026
---

# ScholarForm AI — Template Creation Tutorial

## Table of Contents
- [1. Create Template Folder](#1-create-template-folder)
- [2. Add Jinja2 Tags in DOCX](#2-add-jinja2-tags-in-docx)
- [3. Minimal Template Snippets](#3-minimal-template-snippets)
- [4. Validate the Template](#4-validate-the-template)
- [5. Template Quality Checklist](#5-template-quality-checklist)
- [6. Rollout Steps](#6-rollout-steps)

This guide explains how to create a new manuscript template for the formatter pipeline.

## 1. Create Template Folder

Create a new folder in:

`backend/app/templates/<template_name>/`

Recommended files:

- `template.docx` (required)
- `contract.yaml` (recommended)
- `styles.csl` (optional, for CSL reference style)

Example:

`backend/app/templates/my_journal/template.docx`

## 2. Add Jinja2 Tags in DOCX

Open `template.docx` in Microsoft Word and add Jinja tags where content should render.

Use variables:

- `{{ title }}`
- `{{ abstract }}`
- `{{ page_number }}`

Use loops:

- `{% for author in authors %} ... {% endfor %}`
- `{% for section in sections %} ... {% endfor %}`
- `{% for reference in references %} ... {% endfor %}`

Use conditionals:

- `{% if cover_page %} ... {% endif %}`
- `{% if toc %} ... {% endif %}`
- `{% if page_numbers %} ... {% endif %}`

## 3. Minimal Template Snippets

### Title Block

```jinja
{{ title }}
{% for author in authors %}
{{ author }}
{% endfor %}
```

### Sections

```jinja
{% for section in sections %}
{{ section.heading }}
{% for paragraph in section.paragraphs %}
{{ paragraph }}
{% endfor %}
{% endfor %}
```

### References

```jinja
{% if references %}
References
{% for reference in references %}
{{ reference }}
{% endfor %}
{% endif %}
```

## 4. Validate the Template

Run backend template tests:

```bash
cd backend
python -m pytest tests/test_template_renderer.py
```

Run CSL/template integration:

```bash
python -m pytest tests/integration/test_csl_formatting.py --no-cov
```

## 5. Template Quality Checklist

- No unresolved Jinja tags remain after rendering.
- Cover page appears only when enabled.
- TOC appears only when enabled.
- Page numbers appear only when enabled.
- References render correctly with selected citation style.
- `contract.yaml` matches the expected schema (see `backend/app/pipeline/contract_schema.py`).

## 6. Rollout Steps

1. Add template folder and files.
2. Add template entry to the whitelist in `backend/app/routers/v1/documents.py`.
3. Commit template assets.
4. Run tests.
5. Validate manually using one sample `.docx`, one `.pdf`, and one `.tex`.
6. Release.
