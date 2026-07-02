"""Fix function-level model imports using AST for reliable parsing."""
import ast
import re
from pathlib import Path

PDIR = Path("tests/pipeline")
IMPORT_LINE = "from app.models import PipelineDocument, Block, BlockType, Figure, Table, Equation"
SKIP_MODULES = {"BlockType"}  # app.models re-exports

for fpath in sorted(PDIR.glob("test_*.py")):
    text = fpath.read_text(encoding="utf-8")

    if "from app.models import" not in text:
        continue

    # Find the exact import text (may be a subset of IMPORT_LINE)
    m = re.search(r"^from app\.models import (.+)$", text, re.MULTILINE)
    if not m:
        continue
    original_import = m.group(0)
    model_names = m.group(1).strip()

    # Remove module-level from app.models import
    text = re.sub(r"^from app\.models import .+\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Try parsing with AST to find functions
    # If AST fails (e.g. syntax errors), fall back to regex
    source_lines = text.split("\n")
    new_lines = list(source_lines)
    inserted_lines = set()

    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Find the line number of the first statement in the body
                body_start_line = node.body[0].lineno - 1  # 0-indexed
                func_end_line = node.end_lineno - 1

                # Check if first statement is already an import from app.models
                first_stmt = node.body[0] if node.body else None
                already_has_import = False
                if first_stmt and isinstance(first_stmt, ast.ImportFrom):
                    if getattr(first_stmt, "module", "") == "app.models":
                        already_has_import = True

                if not already_has_import:
                    indent = " " * (node.col_offset + 4)  # body indent = def indent + 4
                    import_stmt = f"{indent}{original_import}"
                    # Insert before the first body statement
                    offset = 0
                    for stmt in node.body:
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Str, ast.Constant)):
                            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                                offset += 1
                                continue
                        break
                    insert_line = body_start_line + offset
                    if insert_line not in inserted_lines:
                        new_lines.insert(insert_line, import_stmt)
                        inserted_lines.add(insert_line)
    except SyntaxError:
        print(f"  ! AST parse failed for {fpath.name}, trying regex fallback")
        # Regex fallback: find every def line and insert import
        lines = text.split("\n")
        new_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            new_lines.append(line)
            if (stripped.startswith("def ") or stripped.startswith("async def ")) and line.rstrip().endswith(":"):
                indent = len(line) - len(stripped)
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                # Check if next non-empty line already has the import
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines) and f"from app.models import" in lines[j]:
                    continue
                new_lines.append(" " * (indent + 4) + original_import)

    new_text = "\n".join(new_lines)
    # Clean up excessive blank lines
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    fpath.write_text(new_text, encoding="utf-8")
    print(f"  + Fixed {fpath.name}")

print("\nDone!")
