"""
Simple fix: move ALL function-level `from app.models import ...` to module level.
Also handles: files where import line exists but broken from Phase 0 mangle.
"""
import ast
import re
import os

BASE = "tests/pipeline"

def fix_one(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")

    # Find ALL function-level from app.models import statements
    func_import_idxs = []
    for i, line in enumerate(lines):
        if re.match(r"^\s+from app\.models import", line):
            func_import_idxs.append(i)

    # Find module-level from app.models import
    has_module_level = any(re.match(r"^from app\.models import", l) for l in lines)

    if not func_import_idxs and has_module_level:
        return False, "already has module-level import, no func-level"

    if not func_import_idxs:
        return False, "no app.models imports found"

    # If there's a module-level import AND func-level imports, just remove func-level
    if has_module_level:
        new_lines = [l for i, l in enumerate(lines) if i not in func_import_idxs]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        try:
            ast.parse("\n".join(new_lines))
            return True, f"removed {len(func_import_idxs)} func-level import(s) (module level exists)"
        except SyntaxError as e:
            return False, f"syntax error after cleanup: {e}"

    # No module-level import - collect all imported names from func-level imports
    all_names = []
    for idx in func_import_idxs:
        line = lines[idx].strip()
        # Extract everything after "from app.models import "
        after = line[len("from app.models import "):]
        after = after.strip("(").strip(")").strip()
        # Split by comma (handling multi-line)
        for part in after.split(","):
            part = part.strip()
            if part:
                all_names.append(part)

    # Remove duplicates preserving order
    seen = set()
    unique_names = []
    for n in all_names:
        if n not in seen:
            seen.add(n)
            unique_names.append(n)

    # Build module-level import
    if len(unique_names) <= 4:
        module_import = "from app.models import " + ", ".join(unique_names)
    else:
        indent = "    "
        module_import = "from app.models import (\n"
        for n in unique_names:
            module_import += indent + n + ",\n"
        module_import += ")"

    # Remove all func-level import lines
    new_lines = [l for i, l in enumerate(lines) if i not in func_import_idxs]

    # Find insertion point for module-level import
    insert_idx = -1
    for i, line in enumerate(new_lines):
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")) and "app.models" not in stripped and "app." not in stripped:
            insert_idx = i + 1
        elif stripped.startswith("from app."):
            insert_idx = i + 1

    if insert_idx < 0:
        insert_idx = 0

    # Add blank line before if needed
    if insert_idx > 0 and new_lines[insert_idx - 1].strip() != "":
        new_lines.insert(insert_idx, "")
        insert_idx += 1

    if "\n" in module_import:
        parts = module_import.split("\n")
        for idx, part in enumerate(parts):
            new_lines.insert(insert_idx + idx, part)
    else:
        new_lines.insert(insert_idx, module_import)

    content2 = "\n".join(new_lines)

    # Fix any remaining orphaned continuation lines from the old import
    # Lines that are just model names with commas at indent level
    cleaned = []
    for line in new_lines:  # Use new_lines directly
        stripped2 = line.strip()
        if (stripped2.endswith(",") and line[0] in (" ", "\t") and 
            any(stripped2.startswith(n) for n in unique_names)):
            continue
        if stripped2 == ")" and line[0] in (" ", "\t"):
            continue
        cleaned.append(line)
    content2 = "\n".join(cleaned)

    try:
        ast.parse(content2)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content2)
        return True, f"moved {len(func_import_idxs)} import(s) to module level: {unique_names}"
    except SyntaxError as e:
        return False, f"syntax error: line {e.lineno}: {e.msg}"


def main():
    fixed = 0
    failed = 0
    for fname in sorted(os.listdir(BASE)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(BASE, fname)
        success, msg = fix_one(path)
        if success:
            print(f"OK: {fname} -> {msg}")
            fixed += 1
        elif "no app.models" not in msg and "already has" not in msg:
            print(f"FAIL: {fname} -> {msg}")
            failed += 1

    print(f"\nFixed: {fixed}, Failed: {failed}")


if __name__ == "__main__":
    main()
