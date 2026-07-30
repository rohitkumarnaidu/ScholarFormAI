# Automated Manuscript Formatter

**Enterprise-grade formatting of academic manuscripts into professionally styled DOCX documents.**

AMF automates the tedious process of formatting academic manuscripts according to citation style guidelines. Write your content in Markdown, LaTeX, or plain text — AMF handles the rest.

## Why AMF?

- **9+ Citation Styles** — APA 7th, MLA 9th, Chicago 17th, IEEE, Harvard, and more
- **Multiple Input Formats** — Markdown, LaTeX, plain text
- **Friction-Free** — No signup, no accounts, no learning curve
- **Open Source** — MIT License, hosted or self-deployed

## Quick Links

- [Installation Guide](getting-started/installation.md)
- [Quick Start](getting-started/quickstart.md)
- [API Reference](api/reference.md)
- [CLI Reference](cli/reference.md)
- [Deployment Guide](deployment/docker.md)

## Quick Start

=== "Docker"

    ```bash
    docker compose up -d
    # Open http://localhost:3000
    ```

=== "CLI"

    ```bash
    pip install amf-cli
    amf init my-paper
    amf format -i my-paper/manuscript.md -s apa
    ```

=== "Python SDK"

    ```python
    from amf_sdk import AMFClient
    client = AMFClient()
    styles = client.get_styles()
    ```

## Supported Styles

| Style | Version | Discipline |
| ------- | --------- | ------------ |
| APA | 7th Edition | Social Sciences, Psychology |
| MLA | 9th Edition | Humanities, Literature |
| Chicago | 17th Edition | History, Arts |
| IEEE | 2023 | Engineering, Computer Science |
| Harvard | 2023 | Multi-discipline |
| Vancouver | 2023 | Biomedical |
| Turabian | 9th Edition | Student Papers |
| ACS | 2023 | Chemistry |
| AMA | 11th Edition | Medical Research |
