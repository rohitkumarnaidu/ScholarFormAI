# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from app.models import Block, BlockType, PipelineDocument, TextStyle
from app.pipeline.structure_detection.detector import StructureDetector


def verify():
    print("Starting Structural Isolation Verification...")

    # 1. Setup Mock Document
    doc = PipelineDocument(document_id="iso_verify")

    # Body Title
    doc.blocks.append(
        Block(
            block_id="b0", text="Main Document Title", index=0, block_type=BlockType.UNKNOWN, style=TextStyle(bold=True)
        )
    )

    # Header Block (Should be isolated)
    doc.blocks.append(
        Block(
            block_id="h1",
            text="This is a Header",
            index=1,
            block_type=BlockType.UNKNOWN,
            style=TextStyle(),
            metadata={"is_header": True},
        )
    )

    # Main Heading
    doc.blocks.append(
        Block(block_id="b1", text="1. Introduction", index=2, block_type=BlockType.UNKNOWN, style=TextStyle(bold=True))
    )

    # Body Text under Intro
    doc.blocks.append(
        Block(block_id="b2", text="Some body text.", index=3, block_type=BlockType.UNKNOWN, style=TextStyle())
    )

    # Footer Block (Should be isolated)
    doc.blocks.append(
        Block(
            block_id="f1",
            text="Page 1",
            index=4,
            block_type=BlockType.UNKNOWN,
            style=TextStyle(),
            metadata={"is_footer": True},
        )
    )

    # 2. Process
    detector = StructureDetector()
    detector.process(doc)

    # 3. Assert Invariants
    header = doc.get_block_by_id("h1")
    footer = doc.get_block_by_id("f1")
    body_text = doc.get_block_by_id("b2")

    print(f"Header section_name: {header.section_name}")
    print(f"Footer section_name: {footer.section_name}")
    print(f"Body Text section_name: {body_text.section_name}")

    # Header/Footer must have None section_name
    assert header.section_name is None, "Header should not have a section name"
    assert footer.section_name is None, "Footer should not have a section name"

    # Body text should inherit "Introduction"
    assert body_text.section_name == "Introduction", (
        f"Body text should be in Introduction (got {body_text.section_name})"
    )

    # Header/Footer must not be heading candidates
    assert not header.metadata.get("is_heading_candidate"), "Header should not be a heading candidate"
    assert not footer.metadata.get("is_heading_candidate"), "Footer should not be a heading candidate"

    # Header/Footer must not have parent_id
    assert header.parent_id is None, "Header should not have a parent_id"
    assert footer.parent_id is None, "Footer should not have a parent_id"

    print("\n✅ VERIFICATION SUCCESS: Header/Footer blocks are structurally isolated.")


if __name__ == "__main__":
    verify()
