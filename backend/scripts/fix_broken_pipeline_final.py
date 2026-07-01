"""Fix all broken pipeline test files comprehensively.

This handles:
1. Missing module-level imports (names used at module level but import stripped)
2. Import lines inside function signatures (invalid syntax)
3. Orphaned continuation lines after stripped imports
"""
import ast
import re
import os
import glob

BASE = "tests/pipeline"
MODEL_NAMES = {
    "BlockType", "Block", "PipelineDocument", "DocumentMetadata",
    "TemplateInfo", "Figure", "Table", "Reference", "Document",
    "ReviewStatus", "ReviewMetadata", "TableCell", "TextStyle",
    "ImageFormat", "Equation", "StyleConfig", "FontConfig",
    "TableCell", "FontConfig",
}


def check_syntax(content):
    try:
        ast.parse(content)
        return None
    except SyntaxError as e:
        return e


def fix_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")

    error = check_syntax(content)
    if error is None:
        # File is syntactically valid - check for missing module-level imports
        return fix_missing_module_imports(path, content, lines)
    else:
        return fix_syntax_error(path, content, lines, error)


def fix_missing_module_imports(path, content, lines):
    """Add module-level from app.models import ... if names are used at module level."""
    # Check which model names appear at module level (before any def/class)
    nesting = 0
    module_lines = []
    for line in lines:
        stripped = line.strip()
        if nesting == 0:
            module_lines.append(stripped)
        if stripped.startswith(("def ", "class ", "@")):
            nesting += 1
        elif nesting > 0 and stripped == "":
            pass

    needed = set()
    for name in MODEL_NAMES:
        # Check if name is referenced in module-level lines (as identifier, not substring)
        if any(re.search(rf"\b{name}\b", ml) for ml in module_lines if ml):
            needed.add(name)

    if not needed:
        return False, "no module-level model references needed"

    # Check if there's already a module-level from app.models import
    has_module_import = any(
        re.match(r"^from app\.models import", l) for l in lines
    )
    if has_module_import:
        return False, "module-level import already exists"

    # Find insertion point: after last stdlib/third-party import
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^(import |from )", stripped) and "app." not in stripped:
            insert_idx = i + 1
        if stripped.startswith("from app."):
            insert_idx = i + 1

    sorted_needed = sorted(needed)
    if len(sorted_needed) <= 4:
        import_line = "from app.models import " + ", ".join(sorted_needed)
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, import_line)
    else:
        indent = "    "
        el = ["from app.models import ("]
        for n in sorted_needed:
            el.append(indent + n + ",")
        el.append(")")
        for idx, imp_line in enumerate(el):
            lines.insert(insert_idx + 1 + idx, imp_line)
        lines.insert(insert_idx, "")

    new_content = "\n".join(lines)
    error = check_syntax(new_content)
    if error:
        return False, f"syntax error after fix: {error.msg} (line {error.lineno})"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True, f"added module-level import: {sorted_needed}"


def fix_syntax_error(path, content, lines, error):
    """Fix syntax errors caused by Phase 0 import fix."""
    lineno = error.lineno

    # Pattern 1: Import inside function signature
    # E.g. def _b(\n    from app.models import ...\n    text: str = ...
    if error.msg == "invalid syntax":
        # Find the import line that's in the function signature
        for i in range(max(0, lineno - 5), min(len(lines), lineno + 2)):
            stripped = lines[i].strip()
            if stripped.startswith("from app.") and "models" in stripped:
                # This import is in the wrong place
                import_stmt = stripped
                # Remove it from its current position
                new_lines = [l for idx, l in enumerate(lines) if idx != i]
                # Find the function body (':') and add import there
                result = []
                added = False
                for idx, line in enumerate(new_lines):
                    result.append(line)
                    if not added and line.strip() == ":":
                        # Check if prev line has 'def' or is a param continuation
                        prev = new_lines[idx - 1].strip() if idx > 0 else ""
                        if "def " in prev or prev.endswith(",") or prev.endswith("("):
                            result.append(f"    {import_stmt}")
                            added = True
                if added:
                    new_content = "\n".join(result)
                    err2 = check_syntax(new_content)
                    if not err2:
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        return True, "moved import from signature to function body"
        return False, f"unable to fix syntax error at line {lineno}"

    # Pattern 2: Unexpected indent (orphaned continuation lines)
    if "unexpected indent" in error.msg or "expected an indented block" in error.msg:
        # Remove orphaned continuation lines
        new_lines = []
        skip_orphans = False
        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect orphaned continuation (indented name + comma or ")" at wrong level)
            if skip_orphans:
                if stripped == ")" or stripped.endswith(","):
                    continue
                skip_orphans = False

            if i >= lineno - 2 and stripped.endswith(",") and line[0] in (" ", "\t"):
                # Skip this and all following continuation lines
                j = i
                while j < len(lines):
                    s = lines[j].strip()
                    if s == ")":
                        j += 1
                        break
                    if not s.endswith(",") and s != ")":
                        break
                    j += 1
                i = j - 1
                skip_orphans = False
                continue

            if stripped == ")" and line[0] in (" ", "\t"):
                # Orphaned closing paren - skip it
                continue

            new_lines.append(line)

        # Also check for: the "from app.models import (" line was stripped, leaving just the body
        # Need to rebuild the import
        needed = set()
        for line in lines:
            for name in MODEL_NAMES:
                if re.search(rf"\b{name}\b", line):
                    needed.add(name)

        if needed:
            # Check if module-level import is missing
            has_module_import = any(
                re.match(r"^from app\.models import", l) for l in new_lines
            )
            if not has_module_import:
                sorted_needed = sorted(needed)
                indent = "    "
                el = ["from app.models import ("]
                for n in sorted_needed:
                    el.append(indent + n + ",")
                el.append(")")
                # Insert after last import
                insert_idx = 0
                for i, line in enumerate(new_lines):
                    stripped = line.strip()
                    if re.match(r"^(import |from )", stripped):
                        insert_idx = i + 1
                for idx, imp_line in enumerate(el):
                    new_lines.insert(insert_idx + 1 + idx, imp_line)
                new_lines.insert(insert_idx, "")

        new_content = "\n".join(new_lines)
        err2 = check_syntax(new_content)
        if not err2:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # After fixing syntax, also check for missing module imports
            fix_missing_module_imports(path, new_content, new_lines)
            return True, "fixed orphaned continuation lines"

        return False, f"still broken after indent fix: {err2.msg} (line {err2.lineno})"

    return False, f"unknown syntax error: {error.msg}"


def main():
    files_to_fix = [
        "test_classifier_gaps.py",
        "test_classifier_gaps_final.py",
        "test_integrity.py",
        "test_nlp_analyzer.py",
        "test_orchestrator_gaps.py",
        "test_prompt_builder_comprehensive.py",
        "test_reference_formatter_deep.py",
        "test_structure_detector_deep.py",
        "test_structure_detector_gaps.py",
        "test_template_renderer_gaps.py",
        "test_validation.py",
        "test_validation_gaps.py",
    ]

    fixed = 0
    failed = 0
    for fname in files_to_fix:
        path = os.path.join(BASE, fname)
        if not os.path.exists(path):
            print(f"SKIP (not found): {fname}")
            continue
        success, msg = fix_file(path)
        status = "OK" if success else "FAIL"
        print(f"{status}: {fname} -> {msg}")
        if success:
            fixed += 1
        else:
            failed += 1

    # Also fix ALL files with missing module-level imports
    print("\n--- Fixing all missing module-level imports ---")
    for fname in sorted(os.listdir(BASE)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BASE, fname)
        with open(path, encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")

        # Only fix files without syntax errors
        err = check_syntax(content)
        if err:
            continue

        success, msg = fix_missing_module_imports(path, content, lines)
        if success:
            print(f"FIXED: {fname} -> {msg}")
            fixed += 1

    print(f"\nSummary: {fixed} fixed, {failed} failed")


if __name__ == "__main__":
    main()
