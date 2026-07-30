# Plugin Guide

## Overview

AMF supports extending functionality through a plugin architecture. Plugins can:

- Add new citation styles
- Add new input parsers
- Add new output formats
- Add validation rules

## Plugin Types

### Style Plugin

Add a new citation style:

```python
from app.services.style_registry import FormattingStyle, StyleRegistry

custom_style = FormattingStyle(
    id="my-style",
    name="My Custom Style",
    version="1.0",
    description="A custom academic style",
    citation_format="author-year",
    font_family="Times New Roman",
    font_size=12,
    line_spacing=2.0,
)

registry = StyleRegistry()
registry.register_style(custom_style)
```

### Parser Plugin

Add support for a new input format:

```python
from app.services.parser import ManuscriptParser
from app.api.models import Manuscript

class OrgModeParser(ManuscriptParser):
    def parse(self, text: str) -> Manuscript:
        # Parse Org-mode text into Manuscript model
        pass
```

### Formatter Plugin

Add custom formatting rules:

```python
from docx import Document

def custom_formatting_hook(doc: Document, manuscript, style):
    # Apply custom formatting
    pass
```

## Registration

Plugins are registered via entry points in `setup.py`:

```python
setup(
    entry_points={
        "amf.styles": ["my-style = mypackage.styles:register"],
        "amf.parsers": ["org = mypackage.parsers:OrgModeParser"],
    }
)
```

## Best Practices

1. Follow the existing plugin patterns
2. Register all plugins in setup.py entry points
3. Include clear documentation
4. Provide test coverage
5. Maintain backward compatibility
