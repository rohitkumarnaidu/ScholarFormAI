"""
Move module-level `from app.models import ...` inside the first function.
Handles single-line and multi-line (parenthesized) imports.
"""
import re
from pathlib import Path


def _find_model_import_blocks(lines):
    """Find blocks of module-level `from app.models import` lines.
    Returns list of (start_idx, end_idx) tuples (end is exclusive).
    """
    blocks = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        # Only match module-level (not indented) lines
        if lines[i][0].isspace():
            i += 1
            continue
        if not stripped.startswith("from app.models ") and not stripped.startswith("from app.models."):
            i += 1
            continue
        
        # Check if it's a multi-line parenthesized import
        if "(" in stripped and ")" not in stripped:
            # Multi-line: find the closing paren
            start = i
            i += 1
            depth = 1
            while i < len(lines) and depth > 0:
                stripped2 = lines[i].strip()
                # Stop if we hit another import statement or a def at module level
                # (shouldn't happen but safety)
                depth += stripped2.count("(") - stripped2.count(")")
                i += 1
            blocks.append((start, i))
        else:
            # Single line import
            blocks.append((i, i + 1))
            i += 1
    
    return blocks


def _find_first_function(lines):
    """Find the first function definition (module-level or inside class)."""
    for i, line in enumerate(lines):
        if re.match(r'^(\s*)(?:async\s+)?def\s+', line):
            return i, len(re.match(r'^(\s*)', line).group(1))
    return None, None


def _find_insertion_point(lines, first_def_line, body_indent):
    """Find where to insert imports inside the function body."""
    # Skip the def line and decorators/docstrings, look for a spot after
    # imports that might already be inside the function
    for i in range(first_def_line + 1, len(lines)):
        stripped = lines[i].strip()
        # Skip blank lines, comments, docstrings
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith(('"""', "'''")) and stripped.count('"""' if stripped.startswith('"""') else "'''") < 2:
            # Start of docstring — skip until end
            delim = '"""' if stripped.startswith('"""') else "'''"
            while i < len(lines) and delim not in lines[i]:
                i += 1
            continue
        # If line starts with an import, skip past it
        if stripped.startswith(("from ", "import ")):
            continue
        # If line is indented properly (part of function body), insert before it
        if lines[i].startswith(" " * body_indent):
            return i
    return len(lines)


def fix_file(filepath: Path) -> bool:
    with open(filepath, encoding="utf-8", errors="replace") as f:
        source = f.read()
    
    lines = source.splitlines(keepends=True)
    
    # 1. Find model import blocks
    model_blocks = _find_model_import_blocks(lines)
    if not model_blocks:
        return False
    
    # 2. Find first function definition
    first_def_line, body_indent = _find_first_function(lines)
    if first_def_line is None:
        return False
    
    # 3. Collect model import text and remove from module level
    # Process in reverse order so indices stay valid
    removed_texts = []
    for start, end in sorted(model_blocks, reverse=True):
        removed_texts.append("".join(lines[start:end]))
        del lines[start:end]
    
    removed_texts.reverse()
    
    # 4. Re-find first function (line numbers shifted)
    first_def_line, body_indent = _find_first_function(lines)
    if first_def_line is None:
        return False
    
    # 5. Find insertion point in function body
    insert_pos = _find_insertion_point(lines, first_def_line, body_indent)
    
    # 6. Check which imports already exist in function body
    existing_imports = set()
    for i in range(first_def_line, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith(("from ", "import ")):
            existing_imports.add(stripped)
    
    # 7. Build import text to insert
    inner_indent = " " * (body_indent + 4)
    import_text = ""
    for block_text in removed_texts:
        for line_text in block_text.splitlines(keepends=True):
            ls = line_text.strip()
            if ls and ls not in existing_imports:
                if ")" not in ls and "(" not in ls:
                    # Strip any indentation from parenthesized continuation lines
                    import_text += inner_indent + ls + "\n"
                else:
                    import_text += inner_indent + ls + "\n"
    import_text += "\n"
    
    # 8. Insert at the found position
    lines.insert(insert_pos, import_text)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print(f"  Fixed {filepath.name}")
    return True


if __name__ == "__main__":
    pipeline_dir = Path("tests/pipeline")
    count = 0
    
    for path in sorted(pipeline_dir.glob("test_*.py")):
        content = path.read_text(encoding="utf-8", errors="replace")
        # Check if it has module-level from app.models imports
        has = False
        for line in content.splitlines():
            if not line or line[0].isspace():
                continue
            if line.strip().startswith("from app.models ") or line.strip().startswith("from app.models."):
                has = True
                break
        if has:
            print(f"Processing {path.name}...")
            try:
                if fix_file(path):
                    count += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
    
    print(f"\nDone. Fixed {count} files.")
