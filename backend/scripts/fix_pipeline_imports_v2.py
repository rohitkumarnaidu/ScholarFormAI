"""
Fix ALL pipeline test files that are broken from Phase 0 import fix.

The Phase 0 fix moved `from app.models import ...` from module level into
function bodies. But many files use those names at MODULE LEVEL in fixture
definitions. This script adds the module-level import back where needed.

Also fixes syntax errors caused by orphaned continuation lines and
imports placed inside function signatures.
"""
import ast
import re
import os
import shutil

BASE = "tests/pipeline"

MODEL_NAMES = [
    "BlockType", "Block", "PipelineDocument", "DocumentMetadata",
    "TemplateInfo", "Figure", "Table", "Reference", "Document",
    "ReviewStatus", "ReviewMetadata", "TableCell", "TextStyle",
    "ImageFormat", "Equation", "StyleConfig", "FontConfig",
]


def has_syntax_error(content):
    try:
        ast.parse(content)
        return None
    except SyntaxError as e:
        return e


def add_module_level_import(lines, needed_names):
    """Add `from app.models import X, Y, Z` at module level."""
    if not needed_names:
        return False

    # Check if already has module-level from app.models
    if any(re.match(r"^from app\.models import", l) for l in lines):
        return False

    sorted_needed = sorted(needed_names)
    if len(sorted_needed) <= 4:
        import_line = "from app.models import " + ", ".join(sorted_needed)
    else:
        indent = "    "
        import_line = "from app.models import (\n"
        for n in sorted_needed:
            import_line += indent + n + ",\n"
        import_line += ")"

    # Find insertion point: after last simple import or module docstring
    insert_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) and "app" not in stripped:
            insert_idx = i + 1
        elif stripped.startswith("from app."):
            insert_idx = i + 1
        elif stripped.startswith("# ") or stripped.startswith('"""') or stripped.startswith("'''"):
            pass

    if insert_idx < 0:
        insert_idx = 0

    # Add blank line then import
    if insert_idx > 0 and lines[insert_idx - 1].strip() != "":
        lines.insert(insert_idx, "")
        insert_idx += 1
    lines.insert(insert_idx, import_line)
    if insert_idx + 1 < len(lines) and lines[insert_idx + 1].strip() != "":
        lines.insert(insert_idx + 1, "")

    return True


def find_module_level_refs(lines):
    """Find which model names are referenced at module level."""
    needed = set()
    nesting = 0
    for line in lines:
        stripped = line.strip()
        if nesting == 0:
            for name in MODEL_NAMES:
                if re.search(rf"\b{name}\b", stripped):
                    needed.add(name)
        if stripped.startswith(("def ", "class ", "@")):
            nesting = 1

    # Also check: if the file has `from app.models import` at function level,
    # and uses model names in module-level code, those names are needed.
    has_func_level = any(
        re.match(r"^\s+from app\.models import", l) for l in lines
    )
    has_module_level = any(
        re.match(r"^from app\.models import", l) for l in lines
    )
    return needed, has_func_level, has_module_level


def remove_orphaned_continuations(lines):
    """Remove orphaned continuation lines (from stripped multi-line imports)."""
    result = []
    skip_until = -1
    for i, line in enumerate(lines):
        if i < skip_until:
            continue
        stripped = line.strip()
        # Skip orphaned continuation items (indented name + comma)
        if len(stripped) > 2 and stripped.endswith(",") and line[0] in (" ", "\t") and stripped.split(",")[0].strip().isidentifier():
            # Check if it's part of an import statement - if so skip the whole block up to )
            j = i
            while j < len(lines):
                s = lines[j].strip()
                if s == ")":
                    j += 1
                    break
                if not s.endswith(",") and not s.startswith("from "):
                    break
                j += 1
            i = j
            continue
        # Skip orphaned )
        if stripped == ")" and i > 0 and lines[i-1].strip().endswith(","):
            # This ) likely closes an orphaned import block
            # Check if any previous non-blank line has "from app.models import ("
            found_from = False
            for k in range(i - 5, i):
                if k >= 0 and "from app.models import (" in lines[k]:
                    found_from = True
                    break
            if found_from:
                continue
        result.append(line)
    return result


def fix_import_in_signature(lines):
    """Fix `from app.models import` placed inside a function signature."""
    result = []
    changes = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line is an import inside a function signature
        if re.match(r"^\s+from app\.models import", stripped):
            # Check context: if prev line is a function param
            prev_stripped = lines[i-1].strip() if i > 0 else ""
            if prev_stripped.endswith(",") or prev_stripped.endswith("(") or "def " in prev_stripped or prev_stripped == "":
                # This import is in the wrong place - save it
                import_stmt = stripped
                # Skip this line
                i += 1
                # Find the ':' that ends the function signature
                while i < len(lines):
                    result.append(lines[i])
                    if lines[i].strip() == ":" and i > 0 and "def " in lines[i-1]:
                        # Add import as first line of function body
                        result[i - len(result) + 1] = f"    {import_stmt}"
                        changes += 1
                        break
                    i += 1
                if i < len(lines):
                    i += 1
                continue

        result.append(line)
        i += 1
    return result, changes


def process_file(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()

    original = content
    lines = content.split("\n")
    n_lines = len(lines)
    changes = []

    # Step 1: Fix syntax errors
    # 1a: Remove orphaned continuation lines
    new_lines = remove_orphaned_continuations(lines)
    if len(new_lines) != n_lines:
        changes.append("removed orphaned continuations")
        lines = new_lines
        n_lines = len(new_lines)

    # 1b: Fix imports in function signatures
    new_lines, c = fix_import_in_signature(lines)
    if c > 0:
        changes.append(f"moved {c} import(s) from signature to body")
        lines = new_lines
        n_lines = len(new_lines)

    # Step 2: Add missing module-level imports
    needed, has_func_level, has_module_level = find_module_level_refs(lines)
    if needed and not has_module_level and has_func_level:
        added = add_module_level_import(lines, needed)
        if added:
            changes.append(f"added module-level import: {sorted(needed)}")

    # Step 3: Verify
    new_content = "\n".join(lines)
    error = has_syntax_error(new_content)
    if error:
        return False, f"syntax error at line {error.lineno}: {error.msg}", original, new_content

    if new_content == original:
        return False, "no changes needed", original, original

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True, "; ".join(changes), original, new_content


def main():
    files = sorted(os.listdir(BASE))
    fixed = 0
    failed = 0
    skipped = 0

    for fname in files:
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BASE, fname)

        # Check if file has issues
        with open(path, encoding="utf-8") as f:
            content = f.read()

        err = has_syntax_error(content)
        needed, has_func_level, has_module_level = find_module_level_refs(content.split("\n"))
        has_func_import = any(
            re.match(r"^\s+from app\.models import", l)
            for l in content.split("\n")
        )

        if not err and not (needed and not has_module_level and has_func_import):
            skipped += 1
            continue

        success, msg, orig, new = process_file(path)
        status = "OK" if success else "FAIL"
        if success:
            fixed += 1
            # Show diff
            orig_lines = orig.split("\n")
            new_lines = new.split("\n")
            for i in range(min(len(orig_lines), len(new_lines))):
                if orig_lines[i] != new_lines[i]:
                    print(f"  {fname}:{i+1}: -{orig_lines[i]}")
                    print(f"  {fname}:{i+1}: +{new_lines[i]}")
        else:
            failed += 1
            print(f"  FAIL {fname}: {msg}")

        print(f"{status}: {fname} -> {msg}")

    print(f"\nSummary: {fixed} fixed, {failed} failed, {skipped} unchanged")


if __name__ == "__main__":
    main()
