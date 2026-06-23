# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile


REQUIRED_MARKERS = {
    "title": "{{ title }}",
    "sections_loop": "{% for section in sections %}",
}


def read_document_xml(docx_path: Path) -> str:
    with ZipFile(docx_path) as zf:
        return zf.read("word/document.xml").decode("utf-8", errors="ignore")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    templates_root = Path("app/templates")
    if not templates_root.exists():
        print("Templates directory not found: app/templates")
        return 1

    failed = 0
    template_paths = sorted(templates_root.glob("*/template.docx"))
    for template_path in template_paths:
        template_name = template_path.parent.name
        try:
            xml = read_document_xml(template_path)
        except Exception as exc:
            failed += 1
            print(f"{template_name}: ❌ unreadable ({exc})")
            continue

        missing = [name for name, marker in REQUIRED_MARKERS.items() if marker not in xml]
        if missing:
            failed += 1
            print(f"{template_name}: ❌ missing markers: {', '.join(missing)}")
        else:
            print(f"{template_name}: ✅")

    if failed:
        print(f"\nFailed templates: {failed}")
        return 1

    print(f"\nAll templates valid: {len(template_paths)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
