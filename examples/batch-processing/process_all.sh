#!/bin/bash
# Batch process all manuscripts in a directory
# Usage: ./process_all.sh <input_dir> <style>

INPUT_DIR="${1:-./manuscripts}"
STYLE="${2:-apa}"
OUTPUT_DIR="${3:-./output}"

mkdir -p "$OUTPUT_DIR"

echo "Processing all manuscripts in $INPUT_DIR with $STYLE style..."
echo

for manuscript in "$INPUT_DIR"/*.md; do
    if [ -f "$manuscript" ]; then
        filename=$(basename "$manuscript" .md)
        echo "Formatting: $filename..."
        amf format -i "$manuscript" -s "$STYLE" -o "$OUTPUT_DIR/${filename}_${STYLE}.docx"
        
        if [ $? -eq 0 ]; then
            echo "  ✓ $filename formatted successfully"
        else
            echo "  ✗ $filename failed"
        fi
    fi
done

echo
echo "Batch processing complete. Output in: $OUTPUT_DIR"
