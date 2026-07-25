# Batch Processing Example

This example demonstrates batch processing multiple manuscripts.

## Setup

```bash
# Create manuscripts directory
mkdir -p manuscripts
```

## Usage

```bash
# Process all markdown files in manuscripts/ with APA style
./process_all.sh manuscripts apa output

# Process with MLA style
./process_all.sh manuscripts mla output/mla

# Process with validation first
for f in manuscripts/*.md; do
    amf validate -i "$f" -s apa
    if [ $? -eq 0 ]; then
        amf format -i "$f" -s apa -o "output/$(basename $f .md).docx"
    fi
done
```

## Files

- `process_all.sh` — Batch processing script
- `manuscripts/` — Place your manuscript files here
- `output/` — Generated DOCX files
