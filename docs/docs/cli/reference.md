# CLI Reference

## Installation

```bash
pip install amf-cli
pip install amf-cli[local]    # For local formatting without API
```

## Commands

### `amf format`

Format a manuscript file.

```bash
amf format -i manuscript.md -s apa -o output.docx
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-i, --input` | Yes | — | Input file path |
| `-o, --output` | No | `{input}_formatted.docx` | Output file path |
| `-s, --style` | No | `apa` | Formatting style |
| `-O, --options` | No | — | JSON options string |
| `-w, --watch` | No | — | Watch for file changes |

### `amf validate`

Validate manuscript structure.

```bash
amf validate -i manuscript.md -s apa
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-i, --input` | Yes | — | Input file path |
| `-s, --style` | No | `apa` | Style to validate against |
| `-o, --output` | No | — | Save report as JSON |

### `amf preview`

Generate HTML preview.

```bash
amf preview -i manuscript.md -s apa --open
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-i, --input` | Yes | — | Input file path |
| `-s, --style` | No | `apa` | Formatting style |
| `-o, --output` | No | Temp file | Output HTML path |
| `--open` | No | — | Open in browser |

### `amf init`

Create a new manuscript project.

```bash
amf init -n my-paper -s apa -o ./projects
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-n, --name` | No | `my-manuscript` | Project name |
| `-s, --style` | No | `apa` | Default style |
| `-o, --output` | No | `.` | Output directory |

### `amf styles`

List and manage styles.

```bash
amf styles list
amf styles show apa
amf styles export apa style.json
```

### `amf config`

Show current configuration.

```bash
amf config
```

## Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version |
| `-v, --verbose` | Verbose output |
| `-c, --config` | Custom config file |
| `--help` | Show help |
