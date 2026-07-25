# Contributing to Automated Manuscript Formatter

First off, thank you for considering contributing! We welcome contributions from everyone.

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/automated-manuscript-formatter.git`
3. Create a feature branch: `git checkout -b feat/amazing-feature`
4. Install dependencies: `make install`
5. Make your changes
6. Run tests: `make test`
7. Lint your code: `make lint`
8. Commit with conventional commits: `git commit -m "feat: add amazing feature"`
9. Push and open a PR

## Development Workflow

### Branch Naming

- `feat/description` — New features
- `fix/description` — Bug fixes
- `docs/description` — Documentation changes
- `refactor/description` — Code refactoring
- `test/description` — Test additions/changes
- `chore/description` — Maintenance tasks

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

### Code Style

- **Python**: We use `ruff` for linting and formatting
- **TypeScript/JavaScript**: We use Prettier and ESLint
- **Documentation**: Markdown with prettier formatting

Run `make format` before committing.

## Project Structure

```
automated-manuscript-formatter/
├── backend/          # FastAPI Python backend
├── frontend/         # Next.js TypeScript frontend
├── cli/              # Python CLI tool (Click)
├── sdk/              # Python SDK (httpx)
├── docs/             # MkDocs documentation website
├── examples/         # Sample projects and templates
├── scripts/          # Build and utility scripts
└── .github/          # CI/CD workflows and templates
```

## Testing

- **Backend**: `cd backend && pytest`
- **Frontend**: `cd frontend && npm test`
- **CLI**: `cd cli && pytest`
- **SDK**: `cd sdk && pytest`
- **All**: `make test`

Write tests for any new functionality. Aim for >80% coverage.

## Pull Request Process

1. Ensure tests pass and linting is clean
2. Update documentation if needed
3. Add a changelog entry in CHANGELOG.md
4. The PR will be reviewed by at least one maintainer
5. Squash merge once approved

## Documentation

- All public APIs must have docstrings
- Update relevant docs when changing behavior
- Add examples for new features
- Run `make docs` to build documentation site

## Questions?

Open a [Discussion](https://github.com/amf/automated-manuscript-formatter/discussions) or join our community chat.
