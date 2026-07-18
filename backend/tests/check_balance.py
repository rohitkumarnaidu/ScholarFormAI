"""Check paren balance in test files."""
import os

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

BASE = "pipeline"
files = [
    "test_classifier_gaps.py",
    "test_classifier_gaps_final.py",
    "test_orchestrator_gaps.py",
    "test_template_renderer_gaps.py",
]

for fname in files:
    path = os.path.join(BASE, fname)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    
    total = 0
    for i, line in enumerate(lines):
        bal = count_paren_balance(line)
        total += bal
    
    if total > 0:
        print(f"{fname}: {total} unclosed parens at EOF")
    elif total < 0:
        print(f"{fname}: {abs(total)} extra closing parens at EOF")
    else:
        print(f"{fname}: balanced")
