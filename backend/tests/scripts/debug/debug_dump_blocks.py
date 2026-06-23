# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
from app.pipeline.parsing.parser import DocxParser
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.classification.classifier import ContentClassifier
from app.models.block import BlockType

def dump_blocks(docx_path):
    parser = DocxParser()
    normalizer = Normalizer()
    classifier = ContentClassifier()
    
    doc = parser.parse(docx_path, "debug")
    doc = normalizer.process(doc)
    doc = classifier.process(doc)
    
    print(f"Total Blocks: {len(doc.blocks)}")
    for b in doc.blocks:
        print(f"[{b.index}] {b.block_type}: {b.text[:100]}...")
        if "fig" in b.text.lower() or "figure" in b.text.lower():
            print(f"  ^^^ POTENTIAL CAPTION AT {b.index}")

if __name__ == "__main__":
    dump_blocks("uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx")
