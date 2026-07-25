# Custom Styles

## Overview

AMF supports custom formatting styles through its style registry. You can create styles for specific journals, conferences, or university requirements.

## Creating a Style

```python
from app.services.style_registry import FormattingStyle, StyleRegistry

journal_style = FormattingStyle(
    id="nature-journal",
    name="Nature Journal Style",
    version="1.0",
    description="Custom style for Nature journal submissions",
    citation_format="numbered",
    font_family="Times New Roman",
    font_size=12,
    line_spacing=1.5,
    margin_inches=1.0,
    heading_styles={
        1: {"font_size": 12, "bold": True, "alignment": "left"},
        2: {"font_size": 11, "bold": True, "alignment": "left"},
    },
    reference_format="numbered",
    first_line_indent=0.0,
)

registry = StyleRegistry()
registry.register_style(journal_style)
```

## Style Properties

| Property | Type | Description |
|----------|------|-------------|
| `font_family` | str | Font for body text |
| `font_size` | int | Body text size in points |
| `line_spacing` | float | Line spacing multiplier |
| `margin_inches` | float | Page margins in inches |
| `first_line_indent` | float | Paragraph indent in inches |
| `reference_format` | str | `hanging` or `numbered` |
| `heading_styles` | dict | Per-level heading configuration |
| `title_page` | bool | Include a title page |
| `abstract_required` | bool | Abstract is mandatory |
| `running_header` | bool | Include running header |

## Export/Import

```bash
# Export a built-in style
amf styles export apa apa-style.json

# Import via API
curl -X POST http://localhost:8000/api/v1/styles \
  -H "Content-Type: application/json" \
  -d @custom-style.json
```
