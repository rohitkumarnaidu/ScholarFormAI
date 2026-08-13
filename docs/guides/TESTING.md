# Testing Guide

Quality assurance is paramount for ScholarForm AI. We employ a multi-layered testing strategy to ensure reliability across the frontend, backend, and AI agents.

## Testing Layers

### 1. Unit Testing
Testing isolated functions and components.
- **Backend**: Uses `pytest`. We mock external services (Database, Redis, LLMs).
- **Frontend**: Uses `Jest` and React Testing Library for component rendering and state logic.

### 2. Integration Testing
Testing the interaction between components (e.g., API to Database, Frontend to API).
- **Backend**: `pytest` with a test database (using `testcontainers` or an in-memory SQLite DB if compatible, though PostgreSQL is preferred).
- **API Tests**: Testing FastAPI endpoints using `TestClient`.

### 3. End-to-End (E2E) Testing
Simulating real user workflows (e.g., uploading a file, verifying the formatted output).
- **Tool**: Cypress or Playwright.
- **Scope**: Critical paths only (login, file upload, AI generation prompt).

## Running Tests Locally

### Backend Tests

Navigate to the `backend/` directory:
```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=app tests/

# Run a specific test file
pytest tests/test_agents/test_auditor.py
```

### Frontend Tests

Navigate to the `frontend/` directory:
```bash
# Run unit tests
npm run test

# Run tests in watch mode
npm run test:watch
```

## Testing AI Agents

Testing non-deterministic LLM output requires specific strategies:
1. **Mocking**: For unit tests, mock the LLM client to return predefined JSON structures.
2. **Evaluation Metrics (Evals)**: For integration tests, use a framework to score the agent's output based on exact match (for structured extraction) or semantic similarity.
3. **Golden Datasets**: Maintain a set of raw documents and their verified formatting outputs to detect regressions in the PyMuPDF extraction or agent logic.

## Continuous Integration (CI)

All tests are enforced via GitHub Actions on every pull request. A PR cannot be merged unless:
1. All tests pass.
2. Code coverage does not decrease (checked via Codecov).
3. Linters (`ruff`, `eslint`) report zero errors.

## Cross-References
- [Benchmarks (Performance Testing)](../operations/BENCHMARKS.md)
- [Deployment (CI/CD details)](../operations/DEPLOYMENT.md)
