# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from app.models import Block, BlockType, PipelineDocument, TextStyle
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.structure_detection.detector import StructureDetector


def verify():
    print("Starting Physical Consolidation Verification...")
    
    # 1. Setup Mock Document with Multi-line Heading
    doc = PipelineDocument(document_id="merge_verify")
    
    # Line 1 of heading
    doc.blocks.append(Block(
        block_id="b1", text="1. This is a very long", index=0, 
        block_type=BlockType.UNKNOWN, style=TextStyle(bold=True, font_size=14.0)
    ))
    
    # Line 2 of heading (Continuation)
    doc.blocks.append(Block(
        block_id="b2", text="Multi-line Heading", index=1, 
        block_type=BlockType.UNKNOWN, style=TextStyle(bold=True, font_size=14.0)
    ))
    
    # Normal Body
    doc.blocks.append(Block(
        block_id="b3", text="This is some normal body text that should not merge.", index=2, 
        block_type=BlockType.UNKNOWN, style=TextStyle(font_size=11.0)
    ))

    # 2. Process through Normalizer
    # Normalizer now requires median_font or calculates it.
    normalizer = Normalizer()
    doc = normalizer.process(doc)
    
    print(f"Blocks after Normalization: {len(doc.blocks)}")
    
    # 3. Process through Detector
    detector = StructureDetector()
    doc = detector.process(doc)
    
    # 4. Assert Invariants
    # Should have 2 blocks now: Merged Heading and Body
    assert len(doc.blocks) == 2, f"Expected 2 blocks, got {len(doc.blocks)}"
    
    merged_block = doc.blocks[0]
    body_block = doc.blocks[1]
    
    print(f"Merged Text: '{merged_block.text}'")
    print(f"Merged Metadata: {merged_block.metadata.get('merged_multiline_heading')}")
    print(f"Merged From: {merged_block.metadata.get('merged_from')}")
    
    assert merged_block.text == "1. This is a very long Multi-line Heading", "Text not merged correctly"
    assert merged_block.metadata.get("merged_multiline_heading") is True
    assert merged_block.metadata.get("merged_from") == "b2"
    assert merged_block.index == 0
    assert body_block.index == 1 # Index must be rescaled
    
    # Structure Invariants
    assert merged_block.metadata.get("is_heading_candidate") is True, "Merged block should be a heading candidate"
    assert merged_block.section_name == "This is a very long Multi-line Heading", "Section name incorrect"
    
    print("\n✅ VERIFICATION SUCCESS: Multi-line headings are physically consolidated.")

if __name__ == "__main__":
    verify()
