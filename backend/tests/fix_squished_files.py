"""Fix squished test files - replace literal \n with actual newlines."""
import re
import os

FILES = [
    os.path.join("pipeline", "test_integrity.py"),
    os.path.join("pipeline", "test_classifier_gaps.py"),
    os.path.join("pipeline", "test_classifier_gaps_final.py"),
    os.path.join("pipeline", "test_nlp_analyzer.py"),
    os.path.join("pipeline", "test_orchestrator_gaps.py"),
    os.path.join("pipeline", "test_template_renderer_gaps.py"),
    os.path.join("pipeline", "test_validation_gaps.py"),
]

BASE = os.path.dirname(os.path.abspath(__file__))

for fname in FILES:
    path = os.path.join(BASE, fname)
    with open(path, "rb") as f:
        raw = f.read()
    
    # Replace literal \n (0x5C 0x6E) with actual newline (0x0A)
    # But be careful not to replace already correct newlines
    fixed = raw.replace(b"\\n", b"\n")
    
    # Fix escaped double-quotes that may have been introduced
    # Also handle the case where there might be double \\n
    fixed = fixed.replace(b"\\\\n", b"\n")
    
    with open(path, "wb") as f:
        f.write(fixed)
    
    # Try to parse as Python
    try:
        compile(fixed, path, "exec")
        print(f"OK: {fname}")
    except SyntaxError as e:
        print(f"SYNTAX ERROR in {fname}: {e}")
        # Print the problematic lines
        lines = fixed.split(b"\n")
        if e.lineno:
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 3)
            for i in range(start, end):
                marker = ">>>" if i == e.lineno - 1 else "   "
                print(f"  {marker} {i+1}: {lines[i].decode('utf-8', errors='replace')[:200]}")
    except Exception as e:
        print(f"ERROR in {fname}: {e}")

print("\nDone.")
