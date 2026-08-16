"""Validate all 8 files parse correctly."""

import ast
import os

BASE = os.path.dirname(os.path.abspath(__file__))

FILES = [
    os.path.join("pipeline", "test_integrity.py"),
    os.path.join("pipeline", "test_classifier_gaps.py"),
    os.path.join("pipeline", "test_classifier_gaps_final.py"),
    os.path.join("pipeline", "test_nlp_analyzer.py"),
    os.path.join("pipeline", "test_orchestrator_gaps.py"),
    os.path.join("pipeline", "test_template_renderer_gaps.py"),
    os.path.join("pipeline", "test_validation_gaps.py"),
    "test_guardrails.py",
]

all_ok = True
for fname in FILES:
    path = os.path.join(BASE, fname)
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        ast.parse(content, filename=fname)
        print(f"OK: {fname}")
    except SyntaxError as e:
        print(f"SYNTAX ERROR in {fname}: {e}")
        lines = content.split("\n")
        if e.lineno:
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 3)
            for i in range(start, end):
                marker = ">>>" if i == e.lineno - 1 else "   "
                print(f"  {marker} {i + 1}: {lines[i][:200]}")
        all_ok = False
    except Exception as e:
        print(f"ERROR in {fname}: {e}")
        all_ok = False

if all_ok:
    print("\nAll files parse correctly!")
else:
    print("\nSome files have syntax errors!")
    exit(1)
