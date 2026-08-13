# CLI Reference

The ScholarFormAI Command Line Interface (CLI) allows you to format documents directly from your terminal.

## Installation

Install the CLI via npm:

```bash
npm install -g @scholarform/cli
```

Or via pip:

```bash
pip install scholarform-cli
```

## Authentication

Before using the CLI, you must authenticate:

```bash
scholarform auth login
```
This will prompt you to enter your API key.

## Global Options

- `--verbose, -v`: Enable verbose logging.
- `--help, -h`: Display help information for any command.
- `--json`: Output results in JSON format.

## Commands

### 1. `format`

Formats a local `.docx` file.

**Usage:**
```bash
scholarform format <input-file> --template <template-id> [options]
```

**Options:**
- `--output, -o`: Specify the output file path.
- `--citations`: Automatically format citations.
- `--style`: Override specific style properties.

**Example:**
```bash
scholarform format my_paper.docx --template apa-7 -o my_paper_formatted.docx
```

### 2. `templates`

Lists available formatting templates.

**Usage:**
```bash
scholarform templates list
```

### 3. `jobs`

Manage asynchronous formatting jobs.

**Usage:**
```bash
scholarform jobs status <job-id>
```

## Cross References
- [SDK Guide](../sdk/SDK_GUIDE.md)
- [API Reference](../api/API_REFERENCE.md)
