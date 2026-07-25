# Using the CLI

## Installation

```bash
pip install amf-cli
```

For local formatting (without API server):

```bash
pip install amf-cli[local]
```

## Commands

### `amf format`

```bash
# Format a manuscript
amf format -i paper.md -s apa -o paper.docx

# Watch mode (reformat on file save)
amf format -i paper.md -s apa --watch

# With options
amf format -i paper.md -s ieee -O '{"page_size":"Letter"}'
```

### `amf validate`

```bash
# Validate manuscript
amf validate -i paper.md -s apa

# Save validation report
amf validate -i paper.md -s apa -o report.json
```

### `amf preview`

```bash
# Generate and open preview
amf preview -i paper.md -s apa --open

# Save preview to file
amf preview -i paper.md -s apa -o preview.html
```

### `amf init`

```bash
# Create a new manuscript project
amf init -n my-paper

# Specify style and output directory
amf init -n my-paper -s ieee -o ./projects
```

### `amf styles`

```bash
# List all styles
amf styles list

# Show style details
amf styles show apa

# Export style
amf styles export apa apa-style.json
```

## Configuration

Global config: `~/.config/amf/config.json`
Project config: `./amf.config.json`
