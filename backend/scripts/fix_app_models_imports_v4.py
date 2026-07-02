"""Add model imports to every function body using AST for reliable parsing.
Handles both files with module-level imports and files already partially fixed."""
import ast
import re
from pathlib import Path

PDIR = Path("tests/pipeline")

for fpath in sorted(PDIR.glob("test_*.py")):
    text = fpath.read_text(encoding="utf-8")

    if "from app.models import" not in text:
        continue

    # Find ALL unique import lines used in the file (at any level)
    import_lines_found = set(re.findall(r"from app\.models import (.+)", text))
    if not import_lines_found:
        continue

    # Remove ALL module-level `from app.models import ...` lines
    text = re.sub(r"^from app\.models import .+\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)

    source_lines = text.split("\n")
    modifications = []  # (line_index, import_line)

    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.body:
                continue

            # Check if first body statement is already from app.models
            first_stmt = node.body[0]
            if isinstance(first_stmt, ast.ImportFrom):
                mod = getattr(first_stmt, "module", "") or ""
                if mod == "app.models":
                    continue  # already has the import

            # Use the most common import line from the file
            # (the one with most model names)
            best_import = max(import_lines_found, key=lambda x: len(x))
            indent = " " * (node.col_offset + 4)
            import_stmt = f"{indent}from app.models import {best_import}"

            # Find where to insert: skip docstring
            body_start = node.body[0].lineno - 1  # 0-indexed
            offset = 0
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    offset += 1
                    continue
                break

            insert_at = body_start + offset
            modifications.append((insert_at, import_stmt))

    except SyntaxError as e:
        print(f"  ! AST error in {fpath.name}: {e}")
        continue

    # Apply modifications from bottom to top to preserve line numbers
    modifications.sort(key=lambda x: -x[0])
    for line_idx, imp in modifications:
        source_lines.insert(line_idx, imp)

    new_text = "\n".join(source_lines)
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    fpath.write_text(new_text, encoding="utf-8")
    n_mods = len(modifications)
    if n_mods:
        print(f"  + {fpath.name}: added import to {n_mods} function(s)")
    else:
        print(f"  - {fpath.name}: already correct")

print("\nDone!")
