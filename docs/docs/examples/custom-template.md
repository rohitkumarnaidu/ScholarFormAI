# Custom Template Example

This example demonstrates how to create, configure, and apply custom DOCX templates and specialized Citation Style Language (CSL) files in ScholarForm AI.

## Overview

While standard styles (APA, IEEE, MLA, Chicago) fulfill general publishing guidelines, institutional bodies, university graduate schools, and enterprise publishers frequently mandate specific styling rules:
- Custom font pairings (e.g., Calibri / Georgia instead of Times New Roman).
- Institutional header branding and logos.
- Specialized table and blockquote shading.
- Non-standard citation and bibliography layouts.

ScholarForm AI allows you to supply a custom reference DOCX template and custom CSL XML rules.

---

## 1. Structure of a Custom DOCX Template

A custom DOCX reference template is a Microsoft Word document (`custom_template.docx`) that defines the visual styles used during document generation.

### Key Word Styles to Define:

| Style Name | Description |
| :--- | :--- |
| `Title` | Document title (e.g., 24pt Bold Centered) |
| `Subtitle` | Author names and affiliations (14pt Italic Centered) |
| `Heading 1` | Primary section headings (18pt Bold Primary Color) |
| `Heading 2` | Subsection headings (14pt Bold Secondary Color) |
| `Heading 3` | Sub-subsection headings (12pt Italic) |
| `Normal` | Regular body paragraph text (11pt Regular, Line Spacing 1.15) |
| `Abstract` | Abstract text (10.5pt Italic with 0.5" left/right margins) |
| `Caption` | Figure and table captions (9.5pt Centered) |
| `Header` / `Footer` | Page headers, footers, and page numbers |

---

## 2. Formatting with a Custom Template via CLI

Pass your custom DOCX reference template to the CLI using the `-t` or `--template` flag:

```bash
amf format -i manuscript.md -o output_custom.docx -t templates/custom_template.docx -s apa7
```

### Combining Custom Template and Custom CSL File

If you have a custom CSL XML file (`journal_custom.csl`) for unique citation formatting:

```bash
amf format \
  -i manuscript.md \
  -o output_custom.docx \
  -t templates/custom_template.docx \
  --csl-file templates/journal_custom.csl
```

---

## 3. Registering a Custom Style in Code

If you are extending the ScholarForm AI backend service, register your custom style in `backend/app/services/style_registry.py`:

```python
from app.services.style_registry import StyleRegistry, StyleConfig

custom_style = StyleConfig(
    style_id="university_thesis",
    display_name="University Graduate Thesis Style",
    font_family="Calibri",
    font_size_pt=11.0,
    line_spacing=1.5,
    margin_top_inches=1.0,
    margin_bottom_inches=1.0,
    margin_left_inches=1.5, # Extra margin for binding
    margin_right_inches=1.0,
    citation_style="apa",
    page_numbering="bottom-center"
)

# Register the style
StyleRegistry.register(custom_style)
```

---

## 4. Python SDK Usage with Custom Templates

Apply custom templates programmatically using the Python SDK:

```python
from amf_sdk import AMFClient

client = AMFClient(base_url="http://localhost:8000")

response = client.format_document(
    file_path="manuscript.md",
    output_path="thesis_output.docx",
    template_path="templates/custom_template.docx",
    csl_path="templates/journal_custom.csl"
)

print("Custom formatted document created successfully!")
```
