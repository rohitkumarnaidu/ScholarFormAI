"""Fix module-level `from app.models import *` in pipeline test files."""
import re
from pathlib import Path

pdir = Path("tests/pipeline")

for f in sorted(pdir.glob("test_*.py")):
    content = f.read_text(encoding="utf-8")
    if "from app.models import" not in content:
        continue
    
    lines = content.split("\n")
    new_lines = []
    mod_level_removed = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from app.models import ") and not line.startswith(" ") and not line.startswith("\t"):
            mod_level_removed = True
            continue
        new_lines.append(line)
    
    if not mod_level_removed:
        continue
    
    result = []
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        result.append(line)
        
        if (stripped.startswith("def ") or stripped.startswith("async def ")) and stripped.endswith(":"):
            i += 1
            body_start_found = False
            body_indent = indent + 4
            
            while i < len(new_lines):
                next_line = new_lines[i]
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent <= indent and (next_stripped.startswith("def ") or next_stripped.startswith("async def ") or next_stripped.startswith("class ")):
                    break
                if next_indent == 0 and next_stripped and not next_stripped.startswith("#") and not next_stripped.startswith("\"\"\"") and not next_stripped.startswith("'''") and not next_stripped.startswith("from ") and not next_stripped.startswith("import "):
                    if i > 0 and (new_lines[i-1].strip() == "" or new_lines[i-1].strip().startswith("#")):
                        break
                
                if not body_start_found and next_stripped and not next_stripped.startswith("#") and not next_stripped.startswith("@") and not next_stripped.startswith("\"\"\"") and not next_stripped.startswith("'''"):
                    import_what = re.search(r"from app\.models import (.+)", content).group(1)
                    result.append(" " * body_indent + "from app.models import " + import_what)
                    body_start_found = True
                
                result.append(next_line)
                i += 1
        else:
            i += 1
    
    final = "\n".join(result)
    final = re.sub(r"\n{3,}", "\n\n", final)
    f.write_text(final, encoding="utf-8")
    print("  + Fixed " + f.name)

print("\nDone!")
