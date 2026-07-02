import re
from pathlib import Path

pdir = Path("tests/pipeline")
for f in sorted(pdir.glob("test_*.py")):
    content = f.read_text(encoding="utf-8")
    if re.search(r"^from app\.models import", content, re.MULTILINE):
        print(f.name)
