# Custom Template Example

This example demonstrates creating a custom formatting template.

## Creating a Custom Style

```python
# custom_styles.py
from app.services.style_registry import FormattingStyle, StyleRegistry

def register_custom_styles():
    registry = StyleRegistry()
    
    # Create a custom style for a specific journal
    nature_style = FormattingStyle(
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
        running_header=False,
        title_page=False,
    )
    
    registry.register_style(nature_style)
    print(f"Registered custom style: {nature_style.name}")
```

## Using Custom Styles

```bash
# Via CLI (requires custom style registered on API server)
amf format -i manuscript.md -s nature-journal

# Via SDK
client = AMFClient()
# Custom styles need to be registered on the server first
```

## Template Structure

Custom templates can modify:
- Font family, size, and color
- Heading styles per level
- Line spacing and paragraph spacing
- Margins and page size
- Reference format (hanging, numbered)
- Title page layout
- Running header style
- Page number placement
