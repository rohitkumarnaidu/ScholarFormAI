# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.parsing.parser import DocxParser
from app.pipeline.structure_detection.detector import StructureDetector

parser = DocxParser()
normalizer = Normalizer()
detector = StructureDetector()
classifier = ContentClassifier()

doc = parser.parse("uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx", "test")
doc = normalizer.process(doc)
doc = detector.process(doc)

print(f"Before classification: {len(doc.blocks)} blocks")
doc = classifier.process(doc)
print(f"After classification: {len(doc.blocks)} blocks")

empty_blocks = [b for b in doc.blocks if b.text.strip() == ""]
print(f"\nEmpty blocks found: {len(empty_blocks)}")
for b in empty_blocks:
    print(f"  Block: {b.block_id}")
    print(f"    Type: {b.block_type}")
    print(f"    Index: {b.index}")
    print(f"    Metadata: {b.metadata}")
