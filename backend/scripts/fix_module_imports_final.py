"""
Fix ALL pipeline test files that are missing module-level imports of app.models
types used in fixture definitions at module level.

Phase 0 moved `from app.models import ...` into function bodies, but many files
reference model types in module-level fixture signatures / return types.
"""
import ast
import re
import os

BASE = "tests/pipeline"

MODEL_NAMES = {
    "BlockType", "Block", "PipelineDocument", "DocumentMetadata",
    "TemplateInfo", "Figure", "Table", "Reference", "Document",
    "ReviewStatus", "ReviewMetadata", "TableCell", "TextStyle",
    "ImageFormat", "Equation", "StyleConfig", "FontConfig",
}


def find_missing_imports(path):
    """Find model names used at module level but not imported."""
    with open(path, encoding="utf-8") as f:
        content = f.read()

    try:
        ast.parse(content)
    except SyntaxError:
        return None  # Skip files with syntax errors

    lines = content.split("\n")

    # Check if module-level import exists
    has_module = any(re.match(r"^from app\.models import", l) for l in lines)

    # Extract module-level lines (before first def/class, decorators are module-level)
    module_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("def ", "class ")):
            break
        module_lines.append(line)

    # Find which model names are referenced
    used = set()
    for name in MODEL_NAMES:
        pattern = re.compile(rf"\b{name}\b")
        if any(pattern.search(l) for l in module_lines):
            used.add(name)

    if not used:
        return None

    if has_module:
        return None  # Already has import

    return sorted(used)


def add_import(path, needed):
    """Add `from app.models import ...` at module level."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")

    if len(needed) <= 4:
        import_line = "from app.models import " + ", ".join(needed)
    else:
        indent = "    "
        parts = ["from app.models import ("]
        for n in needed:
            parts.append(indent + n + ",")
        parts.append(")")
        import_line = "\n".join(parts)

    # Insert after last top-level import
    insert_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) and "app.models" not in stripped:
            insert_idx = i + 1
        elif stripped.startswith("from app."):
            insert_idx = i + 1

    if insert_idx < 0:
        insert_idx = 0

    # Add blank line before
    if insert_idx > 0 and lines[insert_idx - 1].strip() != "":
        lines.insert(insert_idx, "")
        insert_idx += 1

    if "\n" in import_line:
        for idx, part in enumerate(import_line.split("\n")):
            lines.insert(insert_idx + idx, part)
        if insert_idx + len(import_line.split("\n")) < len(lines) and lines[insert_idx + len(import_line.split("\n"))].strip() != "":
            lines.insert(insert_idx + len(import_line.split("\n")), "")
    else:
        lines.insert(insert_idx, import_line)
        if insert_idx + 1 < len(lines) and lines[insert_idx + 1].strip() != "":
            lines.insert(insert_idx + 1, "")

    # Also remove the duplicated import from inside function bodies IF it exists
    cleaned = []
    found_func_import = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\s+from app\.models import", stripped):
            found_func_import = True
            continue  # Remove function-level duplicate
        cleaned.append(line)

    new_content = "\n".join(cleaned)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return found_func_import


def main():
    import glob
    fixed = 0
    for fname in sorted(os.listdir(BASE)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BASE, fname)
        needed = find_missing_imports(path)
        if needed is None:
            continue
        removed_func = add_import(path, needed)
        status = f"added {needed}"
        if removed_func:
            status += " (also removed func-level duplicate)"
        print(f"FIXED: {fname} -> {status}")
        fixed += 1

    print(f"\nFixed {fixed} files")


if __name__ == "__main__":
    main()
