# Simple Formatting Example

This example demonstrates basic manuscript formatting with AMF.

## Usage

```bash
# Format with APA style
amf format -i manuscript.md -s apa -o output/manuscript_apa.docx

# Format with MLA style
amf format -i manuscript.md -s mla -o output/manuscript_mla.docx

# Validate before formatting
amf validate -i manuscript.md -s apa
```

## Files

- `manuscript.md` — Sample manuscript in Markdown
- `amf.config.json` — Project configuration
- `output/` — Generated DOCX files
