# Style Guide

## Code Style

### Python

We use [ruff](https://github.com/astral-sh/ruff) for formatting and linting.

```bash
# Format all Python
ruff format .

# Lint all Python
ruff check .
```

Rules:
- Line length: 100 characters
- Quotes: Double quotes for docstrings, single quotes for everything else
- Indentation: 4 spaces
- Type hints required on all public functions
- Docstrings in Google style

### TypeScript/JavaScript

We use Prettier and ESLint.

```bash
# Format all TS/JS
npm run format

# Lint all TS/JS
npm run lint
```

Rules:
- Line length: 100 characters
- Quotes: Single quotes
- Indentation: 2 spaces
- Semicolons required
- Trailing commas: All

## Documentation Style

### Markdown

- Use ATX headings (`#`, `##`, etc.)
- Use fenced code blocks with language tags
- Use tables for structured data
- Use ordered/unordered lists appropriately
- Reference other docs with relative links

### API Documentation

- Include request/response examples
- List all parameters with types
- Document error codes
- Include curl examples

### CLI Documentation

- Document all commands and options
- Include usage examples
- List exit codes
- Show config file format

## Git Style

### Branch Naming

```
feat/description
fix/description
docs/description
refactor/description
test/description
chore/description
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

feat(core): add IEEE citation style support
fix(api): handle empty manuscript sections
docs(readme): update quick start instructions
```
