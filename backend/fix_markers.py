#!/usr/bin/env python3
"""
Audit and apply correct pytest markers across ALL test files.

Scans every test_*.py in tests/, classifies by path & filename, and
adds module-level ``pytestmark = [pytest.mark.<marker>]`` when the
marker is absent from the file content.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent / "tests"
assert BASE.is_dir(), f"tests directory not found at {BASE}"

EXCLUDED_DIRS = {"integration", "fixtures", "scripts", "manual",
                 "golden_files", "__pycache__"}

# ---------------------------------------------------------------------------
#  Classification rules  (unchanged)
# ---------------------------------------------------------------------------

def classify(fp: Path) -> list[str]:
    rel = fp.relative_to(BASE)
    parts = rel.parts
    name = rel.name
    markers: list[str] = []

    for p in parts[:-1]:
        d = p.lower()
        if d == "security":
            markers.append("security")
        elif d == "safety":
            markers.append("chaos")
        elif d == "pipeline":
            markers.append("pipeline")
        elif d == "classifier":
            markers.append("pipeline")
        elif d == "stress":
            markers.append("performance")

    if (name.startswith("test_security_")
            or name in ("test_injection.py", "test_prompt_injection.py",
                        "test_owasp_ai_top10.py", "test_ai_tool_misuse.py")):
        markers.append("security")

    if name.startswith("test_mutation"):
        markers.append("mutation")

    if name.startswith("test_chaos"):
        markers.append("chaos")

    if name.startswith("test_property_based"):
        markers.append("property")

    if (name.startswith("test_observability")
            or name in ("test_prometheus_metrics.py", "test_monitoring.py")):
        markers.append("observability")

    if name.startswith("test_rag") or name.startswith("test_vector_db_"):
        markers.append("rag")

    if name.startswith("test_performance"):
        markers.append("performance")

    if name in ("test_ai_hallucination.py", "test_prompt_regression.py",
                "test_conversation_stability.py", "test_rag_quality.py"):
        markers.append("ai_quality")

    if name.startswith("test_celery"):
        markers.append("database")

    if name in ("test_pipeline.py", "test_pipeline_integration.py",
                "test_pipeline_orchestrator.py",
                "test_pipeline_orchestrator_deep.py",
                "test_pipeline_document.py"):
        markers.append("pipeline")

    seen = set()
    return [m for m in markers if not (m in seen or seen.add(m))]


# ---------------------------------------------------------------------------
#  Content helpers
# ---------------------------------------------------------------------------

def _has_marker(content: str, marker: str) -> bool:
    return f"pytest.mark.{marker}" in content


# Indentation-sensitive block starters that increase depth.
_BLOCK_KEYWORDS = {"def ", "class ", "async def ",
                   "if ", "elif ", "else:",
                   "for ", "while ",
                   "try:", "except ", "except:", "finally:",
                   "with ", "async with "}


def _is_block_start(line: str) -> bool:
    """True if stripped *line* starts a new indented block."""
    s = line.strip()
    if not s or s.startswith("#"):
        return False
    return any(s.startswith(kw) for kw in _BLOCK_KEYWORDS)


def _find_module_level_imports(lines: list[str]) -> tuple[list[int], int]:
    """
    Return (import_line_indices, first_code_line).

    Scans the file tracking indentation depth; only import lines at
    depth 0 (module-level) are returned.
    """
    depth = 0
    import_indices: list[int] = []
    first_code = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()

        # skip empty / comment-only lines
        if not stripped or stripped.startswith("#"):
            continue

        # Compute effective indentation (tabs → 8, spaces as-is)
        raw = line.rstrip("\n").rstrip("\r")
        indent = len(raw) - len(raw.lstrip())

        if indent == 0:
            depth = 0
        elif indent > 0 and depth == 0:
            # entering a block
            if _is_block_start(lines[i - 1]) if i > 0 else False:
                pass  # depth will be managed by the `if indent > 0` condition
            depth = 1

        # We only care about depth == 0 (module-level)
        if indent > 0:
            continue

        if stripped.startswith(("import ", "from ")):
            import_indices.append(i)
            continue

        # Is this a module-level code construct?
        if (stripped.startswith(("class ", "def ", "@", "async def "))
                or stripped.startswith("if __name__")):
            if first_code == len(lines):
                first_code = i
            # Don't break — continue scanning in case there are more imports
            # (unlikely but possible)
            continue

    return import_indices, first_code


def add_pytestmark(content: str, marker: str) -> str:
    """
    Insert module-level ``pytestmark = [pytest.mark.<marker>]``.

    Handles existing ``pytestmark`` in single-value, list, or
    unrecognised (skipif-in-try) formats.
    """
    if _has_marker(content, marker):
        return content

    lines = content.split("\n")

    # ---- Look for existing pytestmark line ----
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("pytestmark "):
            continue

        indent = line[:len(line) - len(line.lstrip())]

        # Inside a try block → conditional pytestmark, skip
        # (scan backwards for "try:" near this line)
        try_block = False
        for j in range(max(0, i - 10), i):
            if lines[j].strip() == "try:":
                try_block = True
                break
        if try_block:
            return content  # can't safely merge

        # Single-value:  pytestmark = pytest.mark.SOMETHING
        m = re.match(r"^pytestmark\s*=\s*pytest\.mark\.(\w+)\s*$", s)
        if m:
            existing = m.group(1)
            lines[i] = f"{indent}pytestmark = [pytest.mark.{existing}, pytest.mark.{marker}]"
            return "\n".join(lines)

        # List:  pytestmark = [pytest.mark.X, ...]
        m = re.match(r"^(pytestmark\s*=\s*\[)", s)
        if m:
            lines[i] = line.rstrip()[:-1] + f", pytest.mark.{marker}]"
            return "\n".join(lines)

        # Unrecognised format — skip
        return content

    # ---- No pytestmark — find module-level insertion point ----
    import_indices, first_code = _find_module_level_imports(lines)

    if import_indices:
        insert_at = import_indices[-1] + 1  # after last module-level import
    elif first_code < len(lines):
        insert_at = first_code  # before first class/def/dec
    else:
        # No imports and no code — append after header comments
        insert_at = 0
        for j in range(min(10, len(lines))):
            if j > 0 and not lines[j].strip() and lines[j - 1].strip().startswith("#"):
                insert_at = j + 1

    lines.insert(insert_at, f"pytestmark = [pytest.mark.{marker}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

summary: list[tuple[Path, list[str]]] = []
skipped_detailed: list[tuple[Path, str]] = []

all_files = sorted(BASE.rglob("test_*.py"))

for fp in all_files:
    rel = fp.relative_to(BASE)
    if any(p in EXCLUDED_DIRS for p in rel.parts):
        continue

    markers = classify(fp)
    if not markers:
        continue

    try:
        original = fp.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"  [ERR]  {rel} — read failed: {exc}")
        continue

    modified = original
    markers_added: list[str] = []

    for m in markers:
        prev = modified
        modified = add_pytestmark(modified, m)
        if modified is not prev:
            markers_added.append(m)

    if markers_added:
        bak = fp.with_suffix(".py.bak")
        if not bak.exists():
            shutil.copy2(str(fp), str(bak))
        fp.write_text(modified, encoding="utf-8")
        summary.append((fp, markers_added))
        print(f"  [ADD]  {rel}  ->  {', '.join(f'@pytest.mark.{m}' for m in markers_added)}")
    else:
        already = [m for m in markers if _has_marker(original, m)]
        skipped_m = [m for m in markers if m not in already]
        if skipped_m:
            skipped_detailed.append((fp, skipped_m))

if skipped_detailed:
    print()
    print(f"  [SKIP] {len(skipped_detailed)} file(s) where markers could not be safely added:")
    for fp, ms in skipped_detailed:
        print(f"         {fp.relative_to(BASE)}  ->  {', '.join(f'@pytest.mark.{m}' for m in ms)}")

print()
print(f"{'=' * 70}")
print(f"  SUMMARY: {len(summary)} test files MODIFIED")
print(f"{'=' * 70}")

marker_counts: dict[str, int] = {}
for _, ms in summary:
    for m in ms:
        marker_counts[m] = marker_counts.get(m, 0) + 1

if marker_counts:
    print("\n  Markers applied (by file count):")
    for m, cnt in sorted(marker_counts.items(), key=lambda x: -x[1]):
        print(f"    @pytest.mark.{m:20s}  ->  {cnt} file(s)")

print(f"\n  Detailed list of modified files:")
for fp, ms in summary:
    ms_str = ", ".join(f"@pytest.mark.{m}" for m in ms)
    print(f"    {fp.relative_to(BASE)}  :  {ms_str}")

print(f"\n  Done. {len(summary)} files updated (backups preserved with .bak suffix).")
