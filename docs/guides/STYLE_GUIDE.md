# Style Guide

This document outlines the coding standards and documentation style guide for contributing to ScholarFormAI. Adhering to these guidelines ensures a consistent, readable, and maintainable codebase.

## 1. Code Style

### Python
- Follow [PEP 8](https://peps.python.org/pep-0008/) strictly.
- Use `black` for code formatting. (Configured in `.pre-commit-config.yaml`)
- Sort imports using `isort`.
- Add type hints to all function signatures (`def process(file: str) -> bool:`).
- Maximum line length is 88 characters (Black default).

### JavaScript / TypeScript
- Use `Prettier` for formatting.
- Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript).
- Use ESLint to enforce rules.
- Prefer `const` over `let`. Never use `var`.

## 2. Documentation Style

### Markdown
- Use standard GitHub Flavored Markdown (GFM).
- Keep lines under 100 characters for plain text where possible.
- Use sentence case for headers (e.g., `## Document processing issues`, not `## Document Processing Issues`).

### Tone and Voice
- **Professional and Clear:** Avoid overly casual language or slang.
- **Active Voice:** Prefer "The API returns an error" over "An error is returned by the API".
- **Direct Instructions:** Use imperative mood for steps (e.g., "Click Save", not "You should click Save").

## 3. Git Commit Messages
We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Format:**
```
<type>(<scope>): <subject>
```

**Allowed Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests

**Example:**
```
feat(parser): add support for parsing nested tables
```

## Further Reading
- [Contributing Guide](../../CONTRIBUTING.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
