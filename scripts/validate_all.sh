#!/bin/bash
# Validate all manuscripts in a directory against a citation style.
#
# Usage:
#   bash scripts/validate_all.sh                    # validates *.md, *.tex in current dir (APA)
#   bash scripts/validate_all.sh ./papers           # validates all in ./papers
#   bash scripts/validate_all.sh ./papers mla       # uses MLA style
#   bash scripts/validate_all.sh ./papers ieee fail # exit on first failure
#
set -euo pipefail

DIR="${1:-.}"
STYLE="${2:-apa}"
FAIL_FAST="${3:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

command -v amf >/dev/null 2>&1 || {
    echo -e "${RED}Error: 'amf' CLI not found.${NC}"
    echo "Install with: pip install -e cli/"
    exit 1
}

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  AMF Batch Validator${NC}"
echo -e "${CYAN}============================================${NC}"
echo -e "Directory: ${BOLD}$DIR${NC}"
echo -e "Style:     ${BOLD}$STYLE${NC}"
echo

if [ ! -d "$DIR" ]; then
    echo -e "${RED}Error: Directory '$DIR' not found.${NC}"
    exit 1
fi

FAILED=0
TOTAL=0

# Find files to validate
FILES=()
while IFS= read -r -d '' f; do
    FILES+=("$f")
done < <(find "$DIR" -maxdepth 1 \( -name "*.md" -o -name "*.tex" -o -name "*.txt" \) -print0 2>/dev/null)

if [ ${#FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}No manuscript files found in '$DIR'.${NC}"
    echo "Supported extensions: .md, .tex, .txt"
    exit 0
fi

echo -e "Found ${#FILES[@]} file(s) to validate"
echo

for f in "${FILES[@]}"; do
    TOTAL=$((TOTAL + 1))
    rel_path="${f#$DIR/}"
    echo -ne "   [$TOTAL/${#FILES[@]}] $rel_path ... "

    if amf validate -i "$f" -s "$STYLE" > /dev/null 2>&1; then
        echo -e "${GREEN}VALID${NC}"
    else
        echo -e "${RED}INVALID${NC}"
        FAILED=$((FAILED + 1))

        # Show validation details
        details=$(amf validate -i "$f" -s "$STYLE" 2>&1 || true)
        if [ -n "$details" ]; then
            echo "$details" | while IFS= read -r line; do
                echo "       $line"
            done
        fi

        if [ "$FAIL_FAST" = "fail" ]; then
            echo
            echo -e "${RED}Fail-fast enabled. Stopping on first failure.${NC}"
            exit 1
        fi
    fi
done

PASSED=$((TOTAL - FAILED))

echo
echo -e "${CYAN}--------------------------------------------${NC}"
echo -e "${CYAN}  Summary${NC}"
echo -e "${CYAN}--------------------------------------------${NC}"
echo -e "  Total:  ${BOLD}$TOTAL${NC}"
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: $([ "$FAILED" -gt 0 ] && echo -e "${RED}$FAILED${NC}" || echo -e "${GREEN}$FAILED${NC}")"
echo

if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}Some files failed validation.${NC}"
    echo "Review the details above and fix issues."
    exit 1
else
    echo -e "${GREEN}All files passed validation!${NC}"
    exit 0
fi
