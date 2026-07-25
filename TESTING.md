# Testing Guide

## Overview

AMF uses pytest for Python testing and Jest for frontend testing.

## Running Tests

```bash
# Run all tests
make test

# Backend tests
cd backend && pytest
cd backend && pytest -v                          # Verbose
cd backend && pytest --cov=app                   # With coverage
cd backend && pytest tests/test_api.py -k "test_format"  # Specific tests

# Frontend tests
cd frontend && npm test
cd frontend && npm test -- --watch               # Watch mode
cd frontend && npm test -- --coverage            # With coverage

# CLI tests
cd cli && pytest

# SDK tests
cd sdk && pytest
```

## Test Structure

```
backend/tests/
├── conftest.py          # Shared fixtures
├── test_api.py          # API endpoint tests
└── test_formatter.py    # Formatter engine tests

cli/tests/
├── conftest.py
└── test_cli.py          # CLI command tests

sdk/tests/
├── conftest.py
└── test_client.py       # SDK client tests
```

## Writing Tests

### Backend (pytest)

```python
def test_format_with_apa(client, sample_manuscript):
    response = client.post("/api/v1/format", json={
        "manuscript": sample_manuscript.model_dump(),
        "style_id": "apa",
    })
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
```

### Frontend (Jest + Testing Library)

```typescript
import { render, screen } from '@testing-library/react';
import { Navbar } from '@/components/Navbar';

describe('Navbar', () => {
  it('renders navigation links', () => {
    render(<Navbar />);
    expect(screen.getByText('Home')).toBeInTheDocument();
  });
});
```

### CLI (Click CliRunner)

```python
from click.testing import CliRunner
from amf.main import cli

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
```

## Coverage Requirements

- **Backend**: Minimum 80% coverage
- **Frontend**: Minimum 70% coverage
- **CLI**: Minimum 75% coverage
- **SDK**: Minimum 80% coverage

Coverage reports are generated in `coverage/` directory.

## Continuous Integration

Tests run automatically on:
- Every pull request
- Every push to main branch
- Release candidates

See `.github/workflows/ci.yml` for details.
