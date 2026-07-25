.PHONY: help install install-dev lint format test test-backend test-frontend test-cli build build-backend build-frontend build-cli build-sdk clean dev-backend dev-frontend dev-docs docker-build docker-up docs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Installation ──────────────────────────────────────────────────────────────

install: ## Install all project dependencies
	cd backend && pip install -r requirements.txt && pip install -r requirements-dev.txt
	cd frontend && npm ci
	cd cli && pip install -e .
	cd sdk && pip install -e .

install-dev: ## Install development dependencies
	pip install pre-commit commitizen
	pre-commit install --hook-type pre-commit --hook-type commit-msg

# ─── Quality ───────────────────────────────────────────────────────────────────

lint: ## Run all linters
	cd backend && ruff check .
	cd frontend && npm run lint
	cd cli && ruff check .
	cd sdk && ruff check .

format: ## Format all code
	cd backend && ruff format .
	cd frontend && npm run format
	cd cli && ruff format .
	cd sdk && ruff format .

# ─── Testing ───────────────────────────────────────────────────────────────────

test: test-backend test-frontend test-cli test-sdk ## Run all tests

test-backend: ## Run backend tests
	cd backend && pytest --cov=app --cov-report=term-missing --cov-report=xml

test-frontend: ## Run frontend tests
	cd frontend && npm test -- --coverage

test-cli: ## Run CLI tests
	cd cli && pytest --cov=amf --cov-report=term-missing

test-sdk: ## Run SDK tests
	cd sdk && pytest --cov=amf_sdk --cov-report=term-missing

# ─── Building ──────────────────────────────────────────────────────────────────

build: build-backend build-frontend build-cli build-sdk ## Build all packages

build-backend: ## Build backend package
	cd backend && python setup.py sdist bdist_wheel

build-frontend: ## Build frontend
	cd frontend && npm run build

build-cli: ## Build CLI package
	cd cli && python setup.py sdist bdist_wheel

build-sdk: ## Build SDK package
	cd sdk && python setup.py sdist bdist_wheel

# ─── Development ───────────────────────────────────────────────────────────────

dev-backend: ## Start backend dev server
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev-docs: ## Start documentation dev server
	cd docs && mkdocs serve

# ─── Docker ────────────────────────────────────────────────────────────────────

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services with Docker
	docker compose up -d

docker-down: ## Stop all Docker services
	docker compose down

# ─── Documentation ─────────────────────────────────────────────────────────────

docs: ## Build documentation site
	cd docs && mkdocs build

docs-deploy: ## Deploy documentation to GitHub Pages
	cd docs && mkdocs gh-deploy

# ─── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Clean all build artifacts
	rm -rf backend/dist backend/build backend/*.egg-info
	rm -rf frontend/.next frontend/out frontend/dist
	rm -rf cli/dist cli/build cli/*.egg-info
	rm -rf sdk/dist sdk/build sdk/*.egg-info
	rm -rf docs/site
	rm -rf .pytest_cache htmlcov coverage .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
