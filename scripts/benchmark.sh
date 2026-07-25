#!/bin/bash
# AMF Benchmark Suite
# Run with: bash scripts/benchmark.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}    AMF Benchmark Suite${NC}"
echo -e "${CYAN}========================================${NC}"
echo
echo "Date: $(date)"
echo "Host: $(hostname 2>/dev/null || echo 'unknown')"
echo "Python: $(python3 --version 2>/dev/null || python --version 2>/dev/null || echo 'not found')"
echo

# Check prerequisites
command -v amf >/dev/null 2>&1 || { echo -e "${RED}Error: 'amf' CLI not found. Install with: pip install -e cli/${NC}"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo -e "${YELLOW}Warning: 'curl' not found. API tests will be skipped.${NC}"; }
command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || { echo -e "${RED}Error: Python not found.${NC}"; exit 1; }

# Test fixture: create sample manuscript if not present
FIXTURE_DIR="test/fixtures"
mkdir -p "$FIXTURE_DIR"

if [ ! -f "$FIXTURE_DIR/sample_short.md" ]; then
    cat > "$FIXTURE_DIR/sample_short.md" << 'EOF'
# Short Benchmark Manuscript
By Benchmark Runner

## Abstract
This is a short test manuscript used for benchmarking.

Keywords: benchmark, test, performance

## Introduction
This is the introduction section of the benchmark manuscript.

## Methodology
We used a standard benchmarking approach to measure performance.

## Results
The results show consistent performance across all tested scenarios.

## Conclusion
Benchmarking is essential for maintaining performance standards.

## References
Benchmark, B. (2024). Benchmarking Methodology. Journal of Performance, 1(1), 1-10.
EOF
fi

if [ ! -f "$FIXTURE_DIR/sample_50p.md" ]; then
    echo -e "${YELLOW}Generating 50-page sample manuscript...${NC}"
    {
        echo "# Long Benchmark Manuscript"
        echo "By Benchmark Runner"
        echo
        echo "## Abstract"
        echo "This is a longer test manuscript used for benchmarking performance with larger documents."
        echo
        echo "Keywords: benchmark, test, performance, long, document"
        echo
        for i in $(seq 1 100); do
            echo "## Section $i"
            echo "This is the content of section $i. It contains multiple paragraphs of text to simulate a real manuscript."
            echo
            echo "Paragraph two of section $i with more detailed content for benchmarking purposes."
            echo
            echo "Paragraph three of section $i with additional text to increase the document length."
            echo
        done
        echo "## References"
        for i in $(seq 1 20); do
            echo "Author$i, F. (2024). Title $i. Journal of Research, $i(1), ${i}00-${i}10."
        done
    } > "$FIXTURE_DIR/sample_50p.md"
fi

PYTHON=$(command -v python3 || command -v python)

# ------------------------------------------------------------------ #
#  1. Formatting Speed Test                                          #
# ------------------------------------------------------------------ #
echo -e "${CYAN}----------------------------------------${NC}"
echo -e "${CYAN}1. Formatting Speed Test (5 runs each)${NC}"
echo -e "${CYAN}----------------------------------------${NC}"

for style in apa mla chicago ieee harvard vancouver; do
    echo -ne "   ${YELLOW}$style:${NC} "
    total=0
    for i in $(seq 1 5); do
        start=$(date +%s%N)
        amf format -i "$FIXTURE_DIR/sample_short.md" -s "$style" -o /dev/null 2>/dev/null
        end=$(date +%s%N)
        elapsed=$(( (end - start) / 1000000 ))
        total=$((total + elapsed))
    done
    avg=$((total / 5))
    echo "${avg}ms avg"
done

# ------------------------------------------------------------------ #
#  2. Large Document Formatting                                       #
# ------------------------------------------------------------------ #
echo
echo -e "${CYAN}----------------------------------------${NC}"
echo -e "${CYAN}2. Large Document Formatting${NC}"
echo -e "${CYAN}----------------------------------------${NC}"

for style in apa ieee; do
    echo -ne "   ${YELLOW}$style (50p):${NC} "
    start=$(date +%s%N)
    amf format -i "$FIXTURE_DIR/sample_50p.md" -s "$style" -o /dev/null 2>/dev/null
    end=$(date +%s%N)
    elapsed=$(( (end - start) / 1000000 ))
    echo "${elapsed}ms"
done

# ------------------------------------------------------------------ #
#  3. API Response Times                                              #
# ------------------------------------------------------------------ #
echo
echo -e "${CYAN}----------------------------------------${NC}"
echo -e "${CYAN}3. API Response Times${NC}"
echo -e "${CYAN}----------------------------------------${NC}"

API_BASE="${AMF_API_BASE:-http://localhost:8000}"

if command -v curl &>/dev/null; then
    endpoints=(
        "$API_BASE/health"
        "$API_BASE/api/v1/styles"
        "$API_BASE/api/v1/styles/apa"
    )

    for url in "${endpoints[@]}"; do
        name=$(echo "$url" | sed "s|$API_BASE||")
        echo -ne "   GET $name: "
        time_total=$(curl -w '%{time_total}' -o /dev/null -s "$url" 2>/dev/null || echo "N/A")
        echo "${time_total}s"
    done

    # POST /api/v1/validate
    echo -ne "   POST /api/v1/validate: "
    time_total=$(curl -w '%{time_total}' -o /dev/null -s -X POST \
        "$API_BASE/api/v1/validate" \
        -H "Content-Type: application/json" \
        -d '{"manuscript":{"title":"Benchmark","sections":[{"heading":"Intro","level":1,"content":[{"text":"Test"}]}]},"style_id":"apa"}' 2>/dev/null || echo "N/A")
    echo "${time_total}s"

    # POST /api/v1/preview
    echo -ne "   POST /api/v1/preview: "
    time_total=$(curl -w '%{time_total}' -o /dev/null -s -X POST \
        "$API_BASE/api/v1/preview" \
        -H "Content-Type: application/json" \
        -d '{"manuscript":{"title":"Benchmark Preview","sections":[{"heading":"Intro","level":1,"content":[{"text":"Preview"}]}]},"style_id":"mla"}' 2>/dev/null || echo "N/A")
    echo "${time_total}s"

else
    echo -e "   ${YELLOW}curl not available, skipping API tests${NC}"
fi

# ------------------------------------------------------------------ #
#  4. Memory Usage                                                    #
# ------------------------------------------------------------------ #
echo
echo -e "${CYAN}----------------------------------------${NC}"
echo -e "${CYAN}4. Memory Usage${NC}"
echo -e "${CYAN}----------------------------------------${NC}"

$PYTHON -c "
import os, sys
try:
    import psutil
    p = psutil.Process(os.getpid())
    mem = p.memory_info()
    print(f'   RSS:  {mem.rss / 1024 / 1024:.1f} MB')
    print(f'   VMS:  {mem.vms / 1024 / 1024:.1f} MB')
    print(f'   USS:  {mem.uss / 1024 / 1024:.1f} MB' if hasattr(mem, 'uss') else '   USS:  N/A')
except ImportError:
    print('   psutil not installed. Install with: pip install psutil')
    print('   Using basic memory info:')
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        print(f'   Max RSS: {usage.ru_maxrss / 1024:.1f} MB')
    except:
        print('   Unable to get memory info')
except AttributeError:
    print('   Memory info not available on this platform')
" 2>/dev/null || echo -e "   ${YELLOW}Unable to get memory info${NC}"

# ------------------------------------------------------------------ #
#  5. Styles information                                              #
# ------------------------------------------------------------------ #
echo
echo -e "${CYAN}----------------------------------------${NC}"
echo -e "${CYAN}5. Available Styles${NC}"
echo -e "${CYAN}----------------------------------------${NC}"

$PYTHON -c "
try:
    from app.services.style_registry import StyleRegistry
    reg = StyleRegistry()
    for s in reg.list_styles():
        print(f'   {s[\"id\"]:12s}  {s[\"name\"]}')
except ImportError:
    print('   (run from project root or install package)')
    print('   apa, mla, chicago, ieee, harvard, vancouver, turabian, acs, ama')
" 2>/dev/null || echo "   apa, mla, chicago, ieee, harvard, vancouver, turabian, acs, ama"

# ------------------------------------------------------------------ #
#  Summary                                                           #
# ------------------------------------------------------------------ #
echo
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Benchmark Complete${NC}"
echo -e "${CYAN}========================================${NC}"
echo
echo "Run k6 for detailed API load testing:"
echo "  k6 run tests/performance/k6-script.js"
echo
echo "Run locust for interactive load testing:"
echo "  locust -f tests/performance/locustfile.py --host=http://localhost:8000"
echo
