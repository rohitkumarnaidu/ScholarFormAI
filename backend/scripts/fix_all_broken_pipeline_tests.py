"""
Fix all broken pipeline test files by analyzing each error pattern.
"""
import ast
import re
import os

BASE = "tests/pipeline"

def parse_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    try:
        ast.parse(content)
        return content, None
    except SyntaxError as e:
        return content, e

def fix_indentation_unexpected_indent(content, lines, e):
    """Pattern: orphaned continuation lines after import was stripped.
    E.g.:
        import pytest
        <blank>
            PipelineDocument,
            ...
        )
    Fix: replace the dangling lines with a proper import block.
    """
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Detect if this line is an orphaned continuation (starts with indent + identifier + comma)
        if stripped.endswith(",") and len(stripped) > 2 and stripped[0].isalpha() and line[0] in (" ", "\t"):
            # This looks like an orphaned import item - skip it and any subsequent continuation
            j = i
            while j < len(lines) and (lines[j].strip().endswith(",") or lines[j].strip() == ")"):
                if lines[j].strip() == ")":
                    j += 1
                    break
                j += 1
            i = j
            continue
        if stripped == ")" and i > 0 and lines[i-1].strip().endswith(","):
            # Orphaned closing paren - skip it
            i += 1
            continue
        new_lines.append(line)
        i += 1
    return new_lines

def fix_import_inside_signature(content, lines, e):
    """Pattern: from app.models import ... placed inside function signature.
    E.g.:
        def _b(
            from app.models import Block, BlockType
            text: str = "run text",
            ...
        )
    Fix: move import to first line of function body.
    """
    import_line = None
    import_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^\s+from app\.models import', line) or re.match(r'^\s+from app\.', line):
            # Check if this is inside a function signature (the line BEFORE has 'def ' and ends with '(')
            prev = lines[i-1].strip() if i > 0 else ""
            # If prev is blank or indented params, this import is a param line
            if prev.endswith(":") or prev == "":
                continue  # It's in the right place
            import_line = line.strip()
            import_idx = i
            break

    if import_line is None:
        return None  # Not fixable by this pattern

    # Remove the import from its current position
    new_lines = [l for l in lines if l.strip() != import_line]
    # Find the function body start and add import there
    result = []
    for i, line in enumerate(new_lines):
        result.append(line)
        stripped = line.strip()
        if stripped == ":" and i > 0 and new_lines[i-1].strip().endswith(":"):
            pass  # Skip false positives
        if stripped == ":" and i > 0 and "def " in new_lines[i-1] if False else False:  # not correct
            pass

    # Simpler approach - find def and add import after the colon
    result = []
    added = False
    for i, line in enumerate(new_lines):
        result.append(line)
        if not added and line.strip() == ":" and i > 0 and new_lines[i-1].strip().startswith("def "):
            # Actually need to check if this is the right def
            pass
        if not added and line.strip().startswith("def ") if False else False:
            pass

    # Even simpler: just insert import as the first line in function body
    # Find ':' preceded by 'def ...(...)'
    result = []
    added = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip the original import line
        if i == import_idx:
            continue
        result.append(line)
        if not added and stripped == ":" and i > 0 and re.match(r'^\s*def\s+\w+\(', lines[i-1]):
            # Check that the NEXT line isn't already the import
            if i + 1 < len(lines) and lines[i+1].strip() == import_line:
                continue  # Already fixed
            result.append(f"    {import_line}")
            added = True

    if not added:
        return None
    return result

def fix_missing_module_import(content, lines, e):
    """Pattern: module-level imports stripped by Phase 0, names used at module level.
    Add a from app.models import ... at the top.
    """
    # Find what names are used but not imported
    # Common names from app.models
    model_names = {
        "BlockType", "Block", "PipelineDocument", "DocumentMetadata",
        "TemplateInfo", "Figure", "Table", "Reference", "Document",
        "ReviewStatus", "ReviewMetadata", "TableCell", "TextStyle",
        "ImageFormat", "Equation", "StyleConfig", "FontConfig",
    }
    used = set()
    for line in lines:
        for name in model_names:
            if name in line and not line.strip().startswith("#") and "from app.models" not in line:
                used.add(name)

    if not used:
        return None

    # Find insertion point (after last top-level import or after module docstring)
    insert_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from __future__", "from app.")):
            insert_idx = i + 1

    # Build import
    indent = "    "
    sorted_used = sorted(used)
    if len(sorted_used) <= 4:
        import_line = "from app.models import " + ", ".join(sorted_used)
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, import_line)
    else:
        import_block = "from app.models import ("
        for n in sorted_used:
            import_block += "\n" + indent + n + ","
        import_block += "\n)"
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, import_block)

    return lines

def fix_circular_import(content, lines):
    """Fix files with `from app.pipeline.generation.content_parser import ...` at module level.
    Move import inside fixture/test functions.
    """
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(r'from app\.pipeline\.generation\.(content_parser|document_generator|prompt_builder)', stripped):
            continue  # Skip module-level import that causes circular import
        new_lines.append(line)
    return new_lines

def main():
    import glob
    files = []
    for f in sorted(os.listdir(BASE)):
        if f.startswith("test_") and f.endswith(".py"):
            files.append(os.path.join(BASE, f))

    fixed_count = 0
    fail_count = 0

    for path in files:
        content, error = parse_file(path)
        if error is None:
            continue  # File is fine

        print(f"\n=== {path} (line {error.lineno}: {error.msg}) ===")
        lines = content.split("\n")

        new_lines = None

        # Pattern 1: IndentationError: unexpected indent (orphaned continuation)
        if "unexpected indent" in error.msg:
            new_lines = fix_indentation_unexpected_indent(content, lines, error)

        # Pattern 2: SyntaxError: invalid syntax (import inside function signature)
        if new_lines is None and "invalid syntax" in error.msg:
            new_lines = fix_import_inside_signature(content, lines, error)

        # Pattern 3: IndentationError: expected an indented block after function definition
        if new_lines is None and "expected an indented block" in error.msg:
            # This could be from missing module-level imports OR corrupted code
            # First try module-level import fix
            new_lines = fix_missing_module_import(content, lines, error)

        # If still None, try generic fix patterns
        if new_lines is None:
            # Try removing orphaned model import items from module level
            new_lines = fix_indentation_unexpected_indent(content, lines, error)

        if new_lines is None:
            print(f"  FAILED: could not determine fix strategy")
            fail_count += 1
            continue

        # Verify the fix
        new_content = "\n".join(new_lines)
        try:
            ast.parse(new_content)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  FIXED")
            fixed_count += 1
        except SyntaxError as e2:
            print(f"  STILL BROKEN (line {e2.lineno}: {e2.msg})")
            # Show context
            nl = new_content.split("\n")
            start = max(0, e2.lineno - 3)
            end = min(len(nl), e2.lineno + 2)
            for i in range(start, end):
                marker = ">>>" if i + 1 == e2.lineno else "   "
                print(f"  {marker} {i+1}: {nl[i]}")
            fail_count += 1

    print(f"\nSummary: {fixed_count} fixed, {fail_count} failed")

if __name__ == "__main__":
    main()
