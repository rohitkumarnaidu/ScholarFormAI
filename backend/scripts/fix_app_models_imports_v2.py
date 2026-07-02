"""Fix module-level `from app.models import *` in pipeline test files.
v2: inserts import into EVERY function body in the file."""
import re
from pathlib import Path

pdir = Path("tests/pipeline")

for f in sorted(pdir.glob("test_*.py")):
    content = f.read_text(encoding="utf-8")
    if "from app.models import" not in content:
        continue
    if not re.search(r"^from app\.models import", content, re.MULTILINE):
        # Already had all model imports inside functions - skip
        continue

    # Find all module-level `from app.models import ...` lines
    import_lines = re.findall(r"^from app\.models import .+", content, re.MULTILINE)
    
    # Remove ALL of them from module level
    content = re.sub(r"^from app\.models import .+\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Now find EVERY function/async function and insert the import at the top of its body
    # We look for lines that start a function definition
    lines = content.split("\n")
    result = []
    i = 0
    modified = False

    while i < len(lines):
        line = lines[i]
        result.append(line)

        # Check: does this line start a function?
        stripped = line.lstrip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            modified = True
            # Find where the colon is - could be on this line or next with \
            j = i
            while j < len(lines) and ":" not in lines[j]:
                j += 1
            # Now advance past the colon line
            while i <= j and i < len(lines):
                if i > j - len(lines) + j:  # wrong logic, just advance properly
                    pass
                if i > j:
                    break
                if i > j:
                    break
                i += 1
            # Now we're at the body
            # Get the function's indentation level
            func_indent = len(line) - len(line.lstrip())
            body_indent = func_indent + 4

            # Collect the body
            body_lines = []
            while i < len(lines):
                cline = lines[i]
                cstripped = cline.strip()
                cindent = len(cline) - len(cstripped)
                
                # Stop conditions: another def/class at same indent
                if cindent <= func_indent and (cstripped.startswith("def ") or cstripped.startswith("async def ") or cstripped.startswith("class ")):
                    break
                # Empty line followed by def/class at same indent
                if cstripped == "" and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_indent = len(next_line) - len(next_line.lstrip())
                    next_stripped = next_line.strip()
                    if next_indent <= func_indent and (next_stripped.startswith("def ") or next_stripped.startswith("async def ") or next_stripped.startswith("class ")):
                        body_lines.append(cline)
                        i += 1
                        break
                
                body_lines.append(cline)
                i += 1

            # Find insertion point: first non-blank, non-comment, non-decorator line
            insert_pos = 0
            for j, bl in enumerate(body_lines):
                bs = bl.strip()
                if bs and not bs.startswith("#") and not bs.startswith("@") and not bs.startswith("\"\"\"") and not bs.startswith("'''"):
                    insert_pos = j
                    break
                insert_pos = j + 1

            # Insert the import line (use the first model import found)
            import_text = "from app.models import " + re.search(r"from app\.models import (.+)", content + " " + "\n".join(body_lines)).group(1)
            if insert_pos >= len(body_lines):
                body_lines.append(" " * body_indent + import_text)
            else:
                body_lines.insert(insert_pos, " " * body_indent + import_text)

            result.extend(body_lines)
        else:
            i += 1

    if modified:
        final = "\n".join(result)
        final = re.sub(r"\n{3,}", "\n\n", final)
        f.write_text(final, encoding="utf-8")
        print("  + Fixed " + f.name)
    else:
        print("  - Skipped " + f.name)

print("\nDone!")
