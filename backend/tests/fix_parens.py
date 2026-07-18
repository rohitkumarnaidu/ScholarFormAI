"""Fix unclosed parentheses by tracking bracket balance per indentation level."""
import os
import re

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline")

FILES = [
    "test_classifier_gaps.py",
    "test_classifier_gaps_final.py",
    "test_orchestrator_gaps.py",
    "test_template_renderer_gaps.py",
]


def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    lines = content.split("\n")
    
    # Strategy: Track indentation levels and find where a block
    # at indent N ends with ], or }, but the next line at indent N-4
    # is NOT a ) but starts a new statement
    
    new_lines = []
    modified = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        if i + 1 >= len(lines):
            continue
        
        stripped = line.lstrip()
        if not stripped:
            continue
        
        indent = len(line) - len(stripped)
        rstrip = stripped.rstrip()
        
        # Check if this line ends a multi-line call that needs closing
        ends_with_comma = rstrip.endswith(",")
        ends_with_bracket = rstrip.endswith("]")
        ends_with_brace = rstrip.endswith("}")
        ends_with_close_paren = rstrip.endswith(")")
        
        if not (ends_with_comma or ends_with_bracket or ends_with_brace):
            continue
        
        next_line = lines[i + 1]
        next_stripped = next_line.lstrip()
        next_indent = len(next_line) - len(next_stripped)
        
        if not next_stripped:
            continue
        
        # If next line is at a lower indentation and doesn't start with ), ], }
        if (next_indent < indent and 
            not next_stripped.startswith(")") and
            not next_stripped.startswith("]") and
            not next_stripped.startswith("}") and
            not next_stripped.startswith("#") and
            next_indent > 0):
            
            # Check backward for the opening statement at `next_indent`
            # that starts a multi-line call (like PipelineDocument, etc.)
            for j in range(i, max(i - 40, -1), -1):
                prev_line = lines[j]
                prev_stripped = prev_line.lstrip()
                prev_indent = len(prev_line) - len(prev_stripped)
                
                if prev_indent < next_indent and prev_stripped:
                    # This is likely the opening statement
                    # If it ends with ( or contains a call pattern
                    if re.search(r'=\s*\w+\($|=\s*\w+\.\w+\($|with\s+\w+\($|\w+\($', prev_stripped):
                        new_lines.append(" " * next_indent + ")")
                        modified = True
                    break
    
    if modified:
        result = "\n".join(new_lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Fixed: {os.path.basename(path)}")
    else:
        print(f"No changes: {os.path.basename(path)}")


for fname in FILES:
    path = os.path.join(BASE, fname)
    if os.path.exists(path):
        fix_file(path)

print("\nDone.")
