<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2026 ScholarForm AI -->

# Template Creation Guide (DOCX + Jinja2)

This guide explains how to create a new manuscript template that works with the `docxtpl` renderer.

## 1. Template Location

Create templates under:

- `app/templates/<style>/template.docx`
- `app/templates/<style>/contract.yaml` (optional but recommended)
- `app/templates/<style>/styles.csl` (optional for CSL reference formatting)

Examples:

- `app/templates/ieee/template.docx`
- `app/templates/apa/template.docx`
- `app/templates/none/template.docx`

## 2. Required Jinja2 Variables

The renderer provides these keys from `TemplateRenderer.build_context(...)`:

- `title`
- `authors` (list)
- `affiliations` (list)
- `date`
- `abstract`
- `keywords` (list)
- `sections` (list of `{heading, paragraphs}`)
- `references` (list of formatted reference strings)

Condition flags:

- `cover_page` (bool)
- `toc` (bool)
- `page_numbers` (bool)
- `page_number` (string, default `"1"`)

## 3. Recommended Base Blocks

Use these patterns in `template.docx` paragraphs:

```jinja
{% if cover_page %}
{{ title }}
{% for author in authors %}{{ author }}{% if not loop.last %}, {% endif %}{% endfor %}
{% if affiliations %}
{% for affiliation in affiliations %}{{ affiliation }}{% if not loop.last %}; {% endif %}{% endfor %}
{% endif %}
{% if toc %}
Table of Contents
{% for section in sections %}{{ loop.index }}. {{ section.heading }}{% endfor %}
{% endif %}
{% if page_numbers %}
Page {{ page_number|default("1") }}
{% endif %}
{% endif %}
```

Sections:

```jinja
{% for section in sections %}
{{ section.heading }}
{% for paragraph in section.paragraphs %}
{{ paragraph }}
{% endfor %}
{% endfor %}
```

References:

```jinja
{% if references %}
References
{% for reference in references %}
{{ reference }}
{% endfor %}
{% endif %}
```

## 4. CSL and References

References are formatted earlier in the pipeline by `ReferenceFormatterEngine` + `CSLEngine`.
In templates, render the final reference text via:

```jinja
{% for reference in references %}
{{ reference }}
{% endfor %}
```

## 5. Validation Checklist

1. No unresolved Jinja tokens remain after rendering (`{{`, `{%`, `{#`).
2. Cover page block appears only when `cover_page=True`.
3. TOC appears only when `toc=True`.
4. Page number line appears only when `page_numbers=True`.
5. References render for `ieee`, `apa`, and `none` styles.

## 6. Commands

Run template-specific tests:

```bash
python -m pytest tests/test_template_renderer.py
```

Run integration tests (CSL + templates):

```bash
python -m pytest tests/integration/test_csl_formatting.py
```
