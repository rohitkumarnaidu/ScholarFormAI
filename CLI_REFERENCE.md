# CLI Reference

## Installation

```bash
pip install amf-cli

# For local formatting (without API server):
pip install amf-cli[local]
```

## Usage

```bash
amf [OPTIONS] COMMAND [ARGS]...
```

### Global Options

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-v, --verbose` | Enable verbose output |
| `-c, --config PATH` | Path to custom config file |
| `--help` | Show help message |

---

## Commands

### `format`

Format a manuscript file into a styled DOCX document.

```bash
amf format -i manuscript.md -o output.docx -s apa
```

| Option | Description |
|--------|-------------|
| `-i, --input PATH` | Input manuscript file (required) |
| `-o, --output PATH` | Output DOCX file path |
| `-s, --style TEXT` | Formatting style (default: `apa`) |
| `-O, --options TEXT` | JSON string of formatting options |
| `-w, --watch` | Watch mode — reformat on file changes |

### `validate`

Validate a manuscript's structure and style compliance.

```bash
amf validate -i manuscript.md -s apa -o report.json
```

| Option | Description |
|--------|-------------|
| `-i, --input PATH` | Input manuscript file (required) |
| `-s, --style TEXT` | Style to validate against |
| `-o, --output PATH` | Output validation report (JSON) |

### `preview`

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

### `styles`

List and manage formatting styles.

```bash
amf styles list
amf styles show apa
amf styles export apa apa-style.json
```

### `init`

Create a new manuscript project with template files.

```bash
amf init -n my-paper -s apa -o ./projects
```

| Option | Description |
|--------|-------------|
| `-n, --name TEXT` | Project name (default: `my-manuscript`) |
| `-s, --style TEXT` | Default formatting style |
| `-o, --output PATH` | Output directory |

### `config`

Show current AMF configuration settings.

```bash
amf config
```

### `issue` / `issues`

Report, manage, and track issues and feature feedback directly from the CLI.

```bash
# Report an issue
amf issue report -t "Heading parsing error" -d "H2 headers are misclassified" -c bug -s high --attach-logs

# List open issues
amf issue list --status new --category bug

# View issue details
amf issue show ISS-1001

# Add a comment
amf issue comment ISS-1001 -b "Fix tested locally"

# Update status or severity
amf issue update ISS-1001 --status resolved

# Search issues
amf issue search "heading"

# Show issue statistics and SLA compliance
amf issue stats

# View label taxonomy
amf issue labels

# Backup issue dataset
amf issue backup
```

| Subcommand | Options & Arguments | Description |
|---|---|---|
| `report` | `-t/--title`, `-d/--description`, `-c/--category`, `-s/--severity`, `-n/--name`, `-e/--email`, `--anonymous`, `--attach-logs` | Submit a new issue report |
| `list` | `--status`, `--category`, `--severity`, `--label`, `--search`, `-l/--limit` | List issues with filtering |
| `show` | `<issue_id>` | Show detailed issue breakdown |
| `comment` | `<issue_id>`, `-b/--body` | Add a comment to an existing issue |
| `update` | `<issue_id>`, `--status`, `--severity`, `--assign`, `--milestone` | Update issue properties |
| `search` | `<query>`, `-l/--limit` | Search issues across fields |
| `stats` | None | Display issue metrics and SLA breaches |
| `labels` | None | List defined labels and colors |
| `backup` | None | Backup local issue data |

### `update`

Manage application update checking, downloads, installation, rollbacks, and release channels.

```bash
# Check for updates
amf update check --channel stable

# Download a specific version
amf update download --version 1.2.0

# Install downloaded update
amf update install

# Rollback to previous version
amf update rollback

# Show update history
amf update history --limit 10

# View release channels
amf update channels

# Update updater settings
amf update settings --auto-check --channel stable

# View release notes
amf update release-notes 1.2.0
```

| Subcommand | Options & Arguments | Description |
|---|---|---|
| `check` | `--channel` | Check for available updates |
| `download` | `--version` | Download update binary/package |
| `install` | None | Apply downloaded update |
| `rollback` | `--version` | Rollback to target version |
| `history` | `--limit` | Display historical update log |
| `channels` | None | List release channels (`stable`, `beta`, `nightly`) |
| `settings` | `--channel`, `--auto-check/--no-auto-check`, `--auto-download`, `--auto-install` | Inspect or update updater settings |
| `release-notes` | `<version>` | View release notes for version |

---

## Configuration File

Location: `~/.amf/config.json` or `amf.config.json` in project root.

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
| 1 | General error / import error |
| 2 | Validation failed |
