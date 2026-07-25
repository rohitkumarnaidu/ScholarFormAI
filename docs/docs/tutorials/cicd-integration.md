# CI/CD Integration

## GitHub Actions

```yaml
# .github/workflows/format.yml
name: Format Manuscripts

on:
  push:
    paths:
      - 'manuscripts/**/*.md'

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Format manuscripts
        run: |
          pip install amf-cli
          mkdir -p formatted
          for file in manuscripts/*.md; do
            echo "Formatting $file..."
            amf validate -i "$file" -s apa
            if [ $? -eq 0 ]; then
              amf format -i "$file" -s apa \
                -o "formatted/$(basename $file .md).docx"
            fi
          done

      - uses: actions/upload-artifact@v4
        with:
          name: formatted-manuscripts
          path: formatted/
```

## GitLab CI

```yaml
stages:
  - validate
  - format

validate:
  stage: validate
  image: python:3.12
  script:
    - pip install amf-cli
    - for f in manuscripts/*.md; do amf validate -i "$f" -s apa; done

format:
  stage: format
  image: python:3.12
  script:
    - pip install amf-cli
    - mkdir -p formatted
    - for f in manuscripts/*.md; do
        amf format -i "$f" -s apa -o "formatted/$(basename $f .md).docx";
      done
  artifacts:
    paths:
      - formatted/
```

## Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: amf-validate
        name: Validate manuscripts
        entry: amf validate -s apa
        language: system
        files: '\.(md|tex)$'
```
