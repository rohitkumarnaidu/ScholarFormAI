# AMF Starter Kit

A ready-to-use starter template for academic manuscript formatting.

## Contents

```
starter-kit/
├── manuscript.md           # Template manuscript
├── amf.config.json         # Project configuration
├── references.bib          # Bibliography
├── Makefile                # Build automation
├── .github/workflows/      # CI/CD pipelines
└── output/                 # Formatted outputs
```

## Getting Started

```bash
# Create a new project from this kit
cp -r starter-kit my-paper
cd my-paper

# Edit your manuscript
vim manuscript.md

# Format it
make format

# Validate it
make validate
```

## Makefile Commands

```bash
make format       # Format with default style
make format-apa   # Format with APA
make format-mla   # Format with MLA
make validate     # Validate manuscript
make preview      # Generate HTML preview
make clean        # Clean output files
```

## Customization

1. Edit `amf.config.json` to change default style and options
2. Add references to `references.bib`
3. Modify the manuscript structure as needed
4. Update the Makefile for additional targets
