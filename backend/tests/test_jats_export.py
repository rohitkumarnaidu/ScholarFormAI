# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
# Fallback if running from backend root
if os.path.abspath(".").endswith("backend") and os.path.abspath(".") not in sys.path:
    sys.path.insert(0, os.path.abspath("."))

from app.models import DocumentMetadata, PipelineDocument, Reference, ReferenceType
from app.pipeline.export.jats_generator import JATSGenerator


def test_jats_export():
    print("--- JATS EXPORT TEST START ---")

    # 1. Mock Document with references
    metadata = DocumentMetadata(title="JATS Test Paper", authors=["Author A", "Author B"])

    # Critical: Reference must have raw_text (fixed in jats_generator.py)
    refs = [
        Reference(
            reference_id="ref_001",
            citation_key="[1]",
            raw_text="Smith, J. (2020). Test Paper. Journal of Testing.",
            index=0,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            authors=["Smith, J."],
            title="Test Paper",
            year=2020,
        )
    ]

    doc = PipelineDocument(document_id="jats_test", original_filename="test.docx", metadata=metadata, references=refs)

    try:
        print("[1/2] Initializing JATSGenerator...")
        generator = JATSGenerator()

        print("[2/2] Generating JATS XML...")
        # This will trigger ref.raw_text access in _add_references
        xml_content = generator.to_xml(doc)

        print("[OK] JATS XML generated successfully")
        print(f"      Length: {len(xml_content)} chars")

        # Save for manual inspection
        output_dir = Path(__file__).parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        xml_path = output_dir / "test_jats.xml"

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

        print(f"[OK] Saved to: {xml_path}")

    except Exception as e:
        print(f"[FAILED] JATS generation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_jats_export()
