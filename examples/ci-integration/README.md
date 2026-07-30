# CI/CD Integration Example

This example demonstrates integrating AMF into your CI/CD pipeline.

## GitHub Actions

```yaml
name: Format Manuscripts
on:
  push:
    paths:
      - 'manuscripts/**/*.md'
      - 'manuscripts/**/*.tex'

jobs:
  format:
    runs-on: ubuntu-latest
    services:
      amf:
        image: ghcr.io/amf/backend:latest
        ports:
          - 8000:8000

    steps:
      - uses: actions/checkout@v4

      - name: Install AMF CLI
        run: pip install amf-cli

      - name: Format manuscripts
        run: |
          mkdir -p formatted
          for file in manuscripts/*.md; do
            echo "Formatting $file..."
            amf format -i "$file" -s apa -o "formatted/$(basename $file .md).docx"
          done

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: formatted-manuscripts
          path: formatted/
```

## GitLab CI

```yaml
stages:
  - format

format:
  stage: format
  image: python:3.12
  services:
    - name: ghcr.io/amf/backend:latest
      alias: amf-api
  variables:
    AMF_API_ENDPOINT: http://amf-api:8000
  script:
    - pip install amf-cli
    - mkdir -p formatted
    - |
      for file in manuscripts/*.md; do
        amf format -i "$file" -s apa -o "formatted/$(basename $file .md).docx"
      done
  artifacts:
    paths:
      - formatted/
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: amf-validate
      name: Validate manuscripts
      entry: amf validate
      language: system
      files: '\.(md|tex)$'
      args: ['-s', 'apa']
```

## Makefile Integration

```makefile
# Format all manuscripts
format-all:
 @for file in $(wildcard manuscripts/*.md); do \
  echo "Formatting $$file..."; \
  amf format -i "$$file" -s apa -o "formatted/$$(basename $$file .md).docx"; \
 done

validate-all:
 @for file in $(wildcard manuscripts/*.md); do \
  amf validate -i "$$file" -s apa; \
 done
```
