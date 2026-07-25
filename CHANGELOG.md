# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-25

### Added

- Core formatting engine supporting 9 academic citation styles
  - APA 7th Edition, MLA 9th Edition, Chicago 17th Edition, IEEE, Harvard, Vancouver, Turabian, ACS, AMA
- Multi-format manuscript parsing (Markdown, LaTeX, plain text)
- Manuscript validation engine with structural and style compliance checks
- Real-time HTML preview generation
- RESTful API with FastAPI
- Modern web UI built with Next.js 14 and Tailwind CSS
- CLI tool with format, validate, preview, init, and styles commands
- Python SDK with sync and async clients
- Upload/process manuscript files via web interface
- Docker support with Docker Compose
- Comprehensive documentation site (MkDocs Material)
- CI/CD pipelines with GitHub Actions
- Pre-commit hooks for code quality
- Concurrent request handling with request ID tracking

### Security

- CORS middleware with configurable origins
- Input validation on all API endpoints
- File upload size limits
- Security headers on frontend
