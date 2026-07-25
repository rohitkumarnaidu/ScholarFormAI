# AMF CLI

Command-line tool for formatting academic manuscripts into professionally styled DOCX documents.

## Installation

```bash
pip install amf-cli
```

For local formatting (without the API server), install with local extras:

```bash
pip install "amf-cli[local]"
```

## Usage

```bash
# Initialize a new manuscript project
amf init my-paper

# Format a manuscript
amf format -i manuscript.md -s apa

# Validate against a style
amf validate -i manuscript.md -s mla

# Preview in browser
amf preview -i manuscript.md -s chicago --open

# List available styles
amf styles list
```

## Configuration

Set environment variables or use `amf config` to configure the API endpoint:

```bash
export AMF_API_URL=http://localhost:8000
```

See [CLI reference](https://amf.dev/docs/cli) for full documentation.
