"""Find pipeline test files where app.models imports were moved inside functions
but module-level fixture definitions still reference those names."""
import re
import os

BASE = "tests/pipeline"
model_names = {
    "BlockType", "Block", "PipelineDocument", "DocumentMetadata",
    "TemplateInfo", "Figure", "Table", "Reference", "Document",
    "ReviewStatus", "ReviewMetadata", "TableCell", "TextStyle",
    "ImageFormat", "Equation", "StyleConfig", "FontConfig",
}

for f in sorted(os.listdir(BASE)):
    if not f.endswith(".py"):
        continue
    path = os.path.join(BASE, f)
    with open(path, encoding="utf-8") as fh:
        content = fh.read()

    # Check for function-level app.models import
    has_function_level = bool(re.search(r"^\s+from app\.models import", content, re.MULTILINE))

    # Check for module-level app.models import
    has_module_level = bool(re.search(r"^from app\.models import", content, re.MULTILINE))

    # Check if model names appear at module level
    lines = content.split("\n")
    nesting = 0
    module_level_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "@")):
            nesting = 1
        elif stripped == "":
            pass
        elif nesting == 0:
            module_level_lines.append(stripped)

    module_uses = set()
    for name in model_names:
        if any(name in line for line in module_level_lines):
            module_uses.add(name)

    if not has_module_level and module_uses:
        print(f"MISSING MODULE IMPORT: {f} -> needs: {module_uses}")
    elif has_function_level and not has_module_level:
        print(f"FUNCTION-LEVEL ONLY: {f}")
