# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.parsing.parser import DocxParser
from app.pipeline.structure_detection.detector import StructureDetector


def inspect_blocks(docx_path):
    parser = DocxParser()
    normalizer = Normalizer()
    detector = StructureDetector()
    classifier = ContentClassifier()
    
    # 1. Parse
    doc = parser.parse(docx_path, "debug")
    print(f"Parser Blocks: {len(doc.blocks)}")
    hf_blocks = [b for b in doc.blocks if b.metadata.get('is_header') or b.metadata.get('is_footer')]
    print(f"H/F in Parser: {len(hf_blocks)}")
    
    # 2. Normalize
    doc = normalizer.process(doc)
    print(f"Normalizer Blocks: {len(doc.blocks)}")
    
    # 3. Detector
    doc = detector.process(doc)
    print(f"Detector Blocks: {len(doc.blocks)}")
    
    # 4. Classifier
    doc = classifier.process(doc)
    print(f"Classifier Blocks: {len(doc.blocks)}")
    
    # Check for TITLE preservation and isolation guards
    print("\nDetailed Block Audit (First 10):")
    for _i, b in enumerate(doc.blocks[:10]):
        print(f"Index {b.index} | Text: {b.text[:30]}...")
        print(f"  - BlockType: {b.block_type}")
        print(f"  - Method: {b.metadata.get('classification_method')}")
        print(f"  - HeadingCandidate: {b.metadata.get('is_heading_candidate')}")
        print(f"  - Is H/F: {b.metadata.get('is_header') or b.metadata.get('is_footer')}")
        print("-" * 40)

if __name__ == "__main__":
    docx = 'uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx'
    inspect_blocks(docx)
