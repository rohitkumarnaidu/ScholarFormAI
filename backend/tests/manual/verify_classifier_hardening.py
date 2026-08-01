# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Verification Script: Classifier Hardening
Purpose: Verify isolation guards and front-matter safety limits in the Classifier.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.models import Block, BlockType, PipelineDocument
from app.pipeline.classification.classifier import ContentClassifier


def test_classifier_hardening():
    print("=" * 70)
    print("VERIFYING CLASSIFIER HARDENING")
    print("=" * 70)
    
    # 1. Setup Mock Blocks
    blocks = []
    
    # Block 0: Title (Protected from Stage 1)
    blocks.append(Block(
        block_id="title",
        text="Forensic Audit of Pipeline Safety",
        index=0,
        block_type=BlockType.TITLE
    ))
    
    # Block 1-21: Long body text (No headings)
    # This should trigger the Front Matter Safety Limit
    for i in range(1, 25):
        blocks.append(Block(
            block_id=f"b{i}",
            text="This is a very long paragraph of body text that goes on for a while to test the safety limit. " * 5,
            index=i,
            block_type=BlockType.UNKNOWN
        ))
        
    # Block 25-26: Headers/Footers (Should be skipped)
    blocks.append(Block(
        block_id="h1",
        text="Header Text",
        index=25,
        block_type=BlockType.UNKNOWN,
        metadata={"is_header": True}
    ))
    blocks.append(Block(
        block_id="f1",
        text="Footer 1",
        index=26,
        block_type=BlockType.UNKNOWN,
        metadata={"is_footer": True}
    ))

    doc = PipelineDocument(
        document_id="test_hardening",
        filename="test.docx",
        blocks=blocks
    )
    
    # 2. Process
    classifier = ContentClassifier()
    doc = classifier.process(doc)
    
    # 3. Assertions
    print("\n[Case 1] TITLE Preservation")
    assert doc.blocks[0].block_type == BlockType.TITLE
    assert doc.blocks[0].metadata.get("classification_method") == "structure_title_preserved"
    print("✅ Title preserved correctly.")

    print("\n[Case 2] Front Matter Safety Limit")
    # Blocks after index 20 should be BODY, not AUTHOR (even without headings)
    for i in range(21, 25):
        block = doc.blocks[i]
        assert block.block_type == BlockType.BODY, f"Block {i} was {block.block_type}, expected BODY"
    print("✅ Front matter zone limited to 20 blocks.")

    print("\n[Case 3] Isolation Guards (Headers/Footers)")
    header_block = next(b for b in doc.blocks if b.block_id == "h1")
    footer_block = next(b for b in doc.blocks if b.block_id == "f1")
    
    assert header_block.block_type == BlockType.UNKNOWN, "Header was classified!"
    assert footer_block.block_type == BlockType.UNKNOWN, "Footer was classified!"
    print("✅ Header/Footer remained UNKNOWN (skipped).")

    print("\n" + "=" * 70)
    print("✅ ALL HARDENING VERIFICATIONS PASSED")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_classifier_hardening()
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)
