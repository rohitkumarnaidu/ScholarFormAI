#!/bin/bash
# Batch format all manuscripts in a directory into multiple citation styles.
#
# Usage:
#   bash scripts/format_all.sh                        # formats all *.md in current dir -> output/ (APA)
#   bash scripts/format_all.sh ./papers               # formats all in ./papers -> ./output/ (APA)
#   bash scripts/format_all.sh ./papers mla ./outdir  # formats to MLA in ./outdir
#   bash scripts/format_all.sh ./papers all ./outdir   # generates all styles for each manuscript
#
set -euo pipefail

DIR="${1:-.}"
STYLE="${2:-apa}"
OUTDIR="${3:-output}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ALL_STYLES=("apa" "mla" "chicago" "ieee" "harvard" "vancouver" "turabian" "acs" "ama")

command -v amf >/dev/null 2>&1 || {
    echo -e "${RED}Error: 'amf' CLI not found.${NC}"
    echo "Install with: pip install -e cli/"
    exit 1
}

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  AMF Batch Formatter${NC}"
echo -e "${CYAN}============================================${NC}"
echo -e "Input directory:  ${BOLD}$DIR${NC}"
echo -e "Style:            ${BOLD}$STYLE${NC}"
echo -e "Output directory: ${BOLD}$OUTDIR${NC}"
echo

# Determine styles to generate
if [ "$STYLE" = "all" ]; then
    TARGET_STYLES=("${ALL_STYLES[@]}")
    echo -e "${YELLOW}Generating all $STYLE styles${NC}"
elif [ "$STYLE" = "quick" ]; then
    TARGET_STYLES=("apa" "mla" "chicago")
    echo -e "${YELLOW}Generating quick styles (apa, mla, chicago)${NC}"
else
    TARGET_STYLES=("$STYLE")
fi

# Create output directory
mkdir -p "$OUTDIR"

# Find input files
FILES=()
while IFS= read -r -d '' f; do
    FILES+=("$f")
done < <(find "$DIR" -maxdepth 1 \( -name "*.md" -o -name "*.tex" -o -name "*.txt" \) -print0 2>/dev/null)

if [ ${#FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}No manuscript files found in '$DIR'.${NC}"
    echo "Supported extensions: .md, .tex, .txt"
    echo
    echo "Creating sample manuscript for testing..."
    mkdir -p "$DIR"
    cat > "$DIR/sample.md" << 'SAMPLE'
# Sample Manuscript for Formatting
By Jane Smith, John Doe

## Abstract
This is a sample manuscript used to test batch formatting functionality.

Keywords: sample, test, formatting, batch

## Introduction
This is the introduction section. It contains background information and context.

## Methodology
We describe our approach to testing batch formatting capabilities.

## Results
The batch formatter successfully processes multiple files with multiple styles.

## Discussion
Batch formatting significantly improves workflow efficiency for researchers.

## Conclusion
Automated formatting saves time and ensures consistency across manuscripts.

## References
Smith, J. (2024). Automated Formatting. Journal of Research, 5(2), 100-110.
Doe, J. (2023). Batch Processing. Computing Letters, 8(4), 200-210.
SAMPLE
    FILES=("$DIR/sample.md")
    echo -e "${GREEN}Created sample.md${NC}"
    echo
fi

echo -e "Found ${#FILES[@]} manuscript file(s)"
echo -e "Generating ${#TARGET_STYLES[@]} style(s) per file"
echo

TOTAL=$(( ${#FILES[@]} * ${#TARGET_STYLES[@]} ))
COUNT=0
FAILED=0

for f in "${FILES[@]}"; do
    basename=$(basename "$f")
    name="${basename%.*}"
    rel_path="${f#$DIR/}"

    for style in "${TARGET_STYLES[@]}"; do
        COUNT=$((COUNT + 1))
        output_file="$OUTDIR/${name}_${style}.docx"
        echo -ne "   [$COUNT/$TOTAL] $rel_path -> ${style} ... "

        if amf format -i "$f" -s "$style" -o "$output_file" > /dev/null 2>&1; then
            if [ -f "$output_file" ] && [ -s "$output_file" ]; then
                size=$(stat -c%s "$output_file" 2>/dev/null || stat -f%z "$output_file" 2>/dev/null || echo "?")
                echo -e "${GREEN}OK${NC} (${size} bytes)"
            else
                echo -e "${YELLOW}WARNING: output file is empty${NC}"
                FAILED=$((FAILED + 1))
            fi
        else
            echo -e "${RED}FAILED${NC}"
            FAILED=$((FAILED + 1))
        fi
    done
done

echo
echo -e "${CYAN}--------------------------------------------${NC}"
echo -e "${CYAN}  Summary${NC}"
echo -e "${CYAN}--------------------------------------------${NC}"
echo -e "  Files processed: ${BOLD}${#FILES[@]}${NC}"
echo -e "  Styles applied:  ${BOLD}${#TARGET_STYLES[@]}${NC}"
echo -e "  Total generated: ${BOLD}$TOTAL${NC}"
echo -e "  Successful:      ${GREEN}$((TOTAL - FAILED))${NC}"
echo -e "  Failed:          $([ "$FAILED" -gt 0 ] && echo -e "${RED}$FAILED${NC}" || echo -e "${GREEN}$FAILED${NC}")"
echo -e "  Output dir:      ${BOLD}$OUTDIR${NC}"

# List output files
echo
echo -e "${CYAN}Generated files:${NC}"
ls -lh "$OUTDIR"/*.docx 2>/dev/null | while IFS= read -r line; do
    echo "  $line"
done 2>/dev/null || echo -e "  ${YELLOW}(no files generated)${NC}"

echo
if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}$FAILED file(s) failed to format.${NC}"
    exit 1
fi
echo -e "${GREEN}All files formatted successfully!${NC}"
