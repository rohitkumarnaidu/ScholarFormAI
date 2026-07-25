# CLI Reference

## Installation

```bash
pip install amf-cli

# For local formatting (without API server):
pip install amf-cli[local]
```

## Usage

```
amf [OPTIONS] COMMAND [ARGS]...
```

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-v, --verbose` | Enable verbose output |
| `-c, --config PATH` | Path to config file |
| `--help` | Show help message |

## Commands

### format

Format a manuscript file into a styled DOCX document.

```bash
amf format -i manuscript.md -o output.docx -s apa
```

| Option | Description |
|--------|-------------|
| `-i, --input PATH` | Input manuscript file (required) |
| `-o, --output PATH` | Output DOCX file path |
| `-s, --style TEXT` | Formatting style (default: apa) |
| `-O, --options TEXT` | JSON string of formatting options |
| `-w, --watch` | Watch mode — reformat on file changes |

### validate

Validate a manuscript's structure and style compliance.

```bash
amf validate -i manuscript.md -s apa -o report.json
```

| Option | Description |
|--------|-------------|
| `-i, --input PATH` | Input manuscript file (required) |
| `-s, --style TEXT` | Style to validate against |
| `-o, --output PATH` | Output validation report (JSON) |

### preview

Generate an HTML preview of the formatted manuscript.

```bash
amf preview -i manuscript.md -s apa --open
```

| Option | Description |
|--------|-------------|
| `-i, --input PATH` | Input manuscript file (required) |
| `-s, --style TEXT` | Formatting style |
| `-o, --output PATH` | Output HTML file path |
| `--open` | Open preview in browser |

### styles

List and manage formatting styles.

```bash
amf styles list
amf styles show apa
amf styles export apa apa-style.json
```

### init

Create a new manuscript project with template files.

```bash
amf init -n my-paper -s apa -o ./projects
```

| Option | Description |
|--------|-------------|
| `-n, --name TEXT` | Project name (default: my-manuscript) |
| `-s, --style TEXT` | Default formatting style |
| `-o, --output PATH` | Output directory |

Creates:
- `manuscript.md` — Template manuscript
- `amf.config.json` — Project configuration
- `references.bib` — BibTeX bibliography

### config

Show current AMF configuration.

```bash
amf config
```

## Configuration File

Location: `~/.config/amf/config.json` (Linux/macOS) or `%APPDATA%/amf/config.json` (Windows)

```json
{
  "style": "apa",
  "api_endpoint": "http://localhost:8000",
  "output_dir": ".",
  "page_size": "A4",
  "font_family": "Times New Roman",
  "font_size": 12,
  "line_spacing": 2.0
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation failed |
