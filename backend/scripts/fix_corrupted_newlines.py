"""Fix corrupted git-HEAD pipeline test files that have literal \n characters."""
import subprocess, re
from pathlib import Path

root = r'C:\Hackathons\ECLearnIX\(Auto AI) Automated Academic Docx Manuscript Formatter\automated-manuscript-formatter'
targets = [
    'backend/tests/pipeline/test_integrity.py',
    'backend/tests/pipeline/test_nlp_analyzer.py',
    'backend/tests/pipeline/test_orchestrator_gaps.py',
    'backend/tests/pipeline/test_template_renderer_gaps.py',
    'backend/tests/pipeline/test_validation.py',
    'backend/tests/pipeline/test_validation_gaps.py',
]

for f in targets:
    r = subprocess.run(['git', 'show', 'HEAD:' + f], cwd=root, capture_output=True)
    raw = r.stdout

    # Check: does this file have literal \n (backslash + n) characters?
    # These files have real newlines in the multiline import at the start,
    # but then literal \n characters for the rest of the content.
    real_newlines = raw.count(b'\n')
    # Count the number of lines if split by real newlines
    lines = raw.split(b'\n')
    # Check each line for literal backslash-n
    has_literal = any(b'\\n' in line for line in lines)

    if not has_literal:
        print(f"  - {f}: no literal \\n found, skipping")
        continue

    print(f"  + {f}: fixing literal \\n ({len(lines)} real lines)")

    # Strategy: the real newlines separate the multiline import
    # (lines[0] = "from app.models import (", lines[1:-6] = continuation, last = ")")
    # After the closing ")", the rest is all literal \n
    
    # Actually, let me check the exact structure
    # The first few lines contain the multiline import with real newlines
    # After that, all content has literal \n
    
    # Find where real newlines end and literal \n begins
    # Usually it's: from app.models import (\n    Block,\n    ...\n)\n\n# SPDX-License-Identifier: MIT\n# ...
    # Where everything AFTER the first \n\n is literal backslash-n

    # Simple approach: replace literal \n with real newlines
    decoded = raw.replace(b'\\n', b'\n')
    # But be careful: don't double-convert already-real newlines
    # Real newlines are 0x0A. Literal '\n' is 0x5C 0x6E
    # raw.replace(b'\\n', b'\n') replaces the two-byte sequence with one byte
    # This is correct!

    # Also fix double-newlines (real \n followed by replacement creates triple)
    decoded = re.sub(b'\n\n\n+', b'\n\n', decoded)

    # Write to the working copy
    local_path = root.replace('\\', '/') + '/backend/' + '/'.join(f.split('/')[1:])
    # Actually just use the relative path from the root
    dest = Path(root) / f[8:]  # strip 'backend/' from the path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(decoded)
    print(f"    Written to {dest}")

print("\nDone!")
