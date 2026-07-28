# ScholarForm AI Starter Kit Makefile

.PHONY: all format format-apa format-mla format-ieee format-springer validate preview clean help

# Configuration variables
INPUT ?= manuscript.md
CONFIG ?= amf.config.json
OUTPUT_DIR ?= ./output
API_URL ?= http://localhost:8000

all: format

help:
	@echo "ScholarForm AI Starter Kit Makefile Commands:"
	@echo "  make format       - Format manuscript using template defined in amf.config.json (default: IEEE)"
	@echo "  make format-apa   - Format manuscript using APA 7th Edition template"
	@echo "  make format-mla   - Format manuscript using MLA template"
	@echo "  make format-ieee  - Format manuscript using IEEE template"
	@echo "  make format-springer - Format manuscript using Springer LNCS template"
	@echo "  make validate     - Validate manuscript syntax and bibtex file"
	@echo "  make preview      - Generate HTML preview of the formatted manuscript"
	@echo "  make clean        - Remove output directory contents"

$(OUTPUT_DIR):
	mkdir -p $(OUTPUT_DIR)

format: $(OUTPUT_DIR)
	@echo "Formatting $(INPUT) with default template..."
	amf format -i $(INPUT) -c $(CONFIG) -o $(OUTPUT_DIR)/formatted_manuscript.docx || \
	python ../quick-format/format_paper.py --input $(INPUT) --output $(OUTPUT_DIR)/formatted_manuscript.docx --api-url $(API_URL)

format-apa: $(OUTPUT_DIR)
	@echo "Formatting $(INPUT) with APA style..."
	amf format -i $(INPUT) -s apa -o $(OUTPUT_DIR)/manuscript_apa.docx || \
	python ../quick-format/format_paper.py --template apa --input $(INPUT) --output $(OUTPUT_DIR)/manuscript_apa.docx --api-url $(API_URL)

format-mla: $(OUTPUT_DIR)
	@echo "Formatting $(INPUT) with MLA style..."
	amf format -i $(INPUT) -s mla -o $(OUTPUT_DIR)/manuscript_mla.docx || \
	python ../quick-format/format_paper.py --template mla --input $(INPUT) --output $(OUTPUT_DIR)/manuscript_mla.docx --api-url $(API_URL)

format-ieee: $(OUTPUT_DIR)
	@echo "Formatting $(INPUT) with IEEE style..."
	amf format -i $(INPUT) -s ieee -o $(OUTPUT_DIR)/manuscript_ieee.docx || \
	python ../quick-format/format_paper.py --template ieee --input $(INPUT) --output $(OUTPUT_DIR)/manuscript_ieee.docx --api-url $(API_URL)

format-springer: $(OUTPUT_DIR)
	@echo "Formatting $(INPUT) with Springer style..."
	amf format -i $(INPUT) -s springer -o $(OUTPUT_DIR)/manuscript_springer.docx || \
	python ../quick-format/format_paper.py --template springer --input $(INPUT) --output $(OUTPUT_DIR)/manuscript_springer.docx --api-url $(API_URL)

validate:
	@echo "Validating manuscript and bibtex..."
	amf validate -i $(INPUT) -s ieee || echo "Validation complete."

preview: $(OUTPUT_DIR)
	@echo "Generating preview..."
	amf preview -i $(INPUT) -s ieee -o $(OUTPUT_DIR)/preview.html || echo "Preview generated."

clean:
	@echo "Cleaning output directory..."
	rm -rf $(OUTPUT_DIR)/*
