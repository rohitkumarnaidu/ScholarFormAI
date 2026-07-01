import re

fixes = {
    "tests/pipeline/test_classifier_gaps.py": ["BlockType"],
    "tests/pipeline/test_classifier_gaps_final.py": ["BlockType"],
    "tests/pipeline/test_integrity.py": ["BlockType"],
    "tests/pipeline/test_nlp_analyzer.py": ["Document"],
    "tests/pipeline/test_reference_formatter_deep.py": ["Reference"],
    "tests/pipeline/test_validation.py": ["Document"],
}

for path, names in fixes.items():
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")

    found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        m = re.match(r"from ([\w.]+) import ", stripped)
        if m and m.group(1) == "app.models":
            existing = stripped[len("from app.models import "):]
            existing = existing.strip("(").strip(")").strip()
            new_imports = existing + ", " + ", ".join(names)
            lines[i] = f"from app.models import {new_imports}"
            found = True
            break

    if not found:
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from __future__")):
                insert_idx = i + 1
        indent = "    "
        import_block = "from app.models import ("
        for n in names:
            import_block += "\n" + indent + n + ","
        import_block += "\n)"
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, import_block)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Fixed: {path}")

print("Done")
