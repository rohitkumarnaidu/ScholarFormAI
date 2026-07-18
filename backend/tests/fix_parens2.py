"""
Fix unclosed parentheses using dedent heuristic.
When a dedicated param-like line (ending with ], }, ), or a comma) 
is followed by a dedented line that starts a new statement, insert a closing paren.
"""
import os
import re

def count_paren_balance(text):
    result = 0
    in_string = None
    escape = False
    for c in text:
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if in_string:
            if c == in_string and not escape:
                in_string = None
            continue
        if c in ('"', "'"):
            in_string = c
            continue
        if c == "(":
            result += 1
        elif c == ")":
            result -= 1
    return result

def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    original = content
    lines = content.split("\n")
    
    iterations = 0
    while iterations < 100:  # safety limit
        # Recalculate paren balance per line
        line_balance = []
        for line in lines:
            line_balance.append(count_paren_balance(line))
        
        cumulative = 0
        inserted = False
        
        for i in range(len(lines) - 1):
            cumulative += line_balance[i]
            if cumulative <= 0:
                cumulative = max(0, cumulative)
                continue
            
            # We're inside at least one open paren
            line = lines[i]
            stripped = line.lstrip()
            if not stripped:
                continue
            indent = len(line) - len(stripped)
            rstrip = stripped.rstrip()
            
            next_line = lines[i + 1]
            next_stripped = next_line.lstrip()
            if not next_stripped:
                continue
            next_indent = len(next_line) - len(next_stripped)
            
            # Check if this line ends a param list (ends with comma, ], }, etc)
            # and next line is dedented and NOT a closing bracket
            is_param_end = (rstrip.endswith(",") or 
                          rstrip.endswith("]") or 
                          rstrip.endswith("}"))
            
            if (is_param_end and 
                next_indent < indent and 
                cumulative > 0 and
                not next_stripped.startswith(")") and
                not next_stripped.startswith("]") and
                not next_stripped.startswith("}") and
                not next_stripped.startswith("#") and
                next_indent > 0):
                
                # We need to close here
                lines.insert(i + 1, " " * next_indent + ")")
                inserted = True
                iterations += 1
                break
        
        if not inserted:
            break
    
    if iterations > 0:
        result = "\n".join(lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Fixed {os.path.basename(path)}: {iterations} parens added")
    else:
        print(f"No changes: {os.path.basename(path)}")
    
    # Verify balance
    total = sum(count_paren_balance(l) for l in lines)
    if total == 0:
        print(f"  -> Balanced: YES")
    else:
        print(f"  -> Balance: {total} (still unbalanced)")
    
    # Verify parse
    try:
        import ast
        ast.parse(result, filename=path)
        print(f"  -> Parse: OK")
    except SyntaxError as e:
        print(f"  -> Parse ERROR: {e}")


BASE = "pipeline"
files = [
    "test_classifier_gaps.py",
    "test_classifier_gaps_final.py",
    "test_orchestrator_gaps.py",
    "test_template_renderer_gaps.py",
]

for fname in files:
    path = os.path.join(BASE, fname)
    fix_file(path)

# Also re-check test_integrity and test_nlp_analyzer
print("\n--- Checking other files ---")
for fname in ["test_integrity.py", "test_nlp_analyzer.py", "test_validation_gaps.py"]:
    path = os.path.join(BASE, fname)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        total = sum(count_paren_balance(l) for l in content.split("\n"))
        try:
            import ast
            ast.parse(content, filename=fname)
            print(f"{fname}: Balance={total}, Parse=OK")
        except SyntaxError as e:
            print(f"{fname}: Balance={total}, Parse ERROR: {e}")
