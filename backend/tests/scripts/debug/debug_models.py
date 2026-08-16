# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

try:
    from app.models import Block, BlockType, DocumentMetadata, PipelineDocument, Reference

    print("--- Testing Reference Instantiation ---")
    try:
        ref = Reference(
            reference_id="ref_1",
            citation_key="Doe2024",
            raw_text="J. Doe... 2024",
            index=0,
            authors=["J. Doe", "A. Smith"],
            title="Test Paper",
            year=2024,
            journal="Test Journal",
        )
        print("✅ Reference instantiated successfully")
    except Exception as e:
        print(f"❌ Reference instantiation failed: {e}")

    print("\n--- Testing Block Instantiation ---")
    try:
        block = Block(
            block_id="title", index=0, text="Test Document", block_type=BlockType.TITLE, classification_confidence=0.95
        )
        print("✅ Block instantiated successfully")
    except Exception as e:
        print(f"❌ Block instantiation failed: {e}")

    print("\n--- Testing PipelineDocument Instantiation ---")
    try:
        doc = PipelineDocument(
            document_id="test_doc", metadata=DocumentMetadata(title="Test Document", authors=["John Doe"])
        )
        doc.blocks = [block]
        print("✅ PipelineDocument instantiated successfully")
    except Exception as e:
        print(f"❌ PipelineDocument instantiation failed: {e}")

except Exception as e:
    print(f"❌ Import failed: {e}")
