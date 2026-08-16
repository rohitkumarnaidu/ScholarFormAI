# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from app.pipeline.classification.classifier import ContentClassifier
from app.pipeline.formatting.formatter import Formatter
from app.pipeline.normalization.normalizer import Normalizer
from app.pipeline.parsing.parser import DocxParser


def debug_render(docx_path, out_path):
    parser = DocxParser()
    normalizer = Normalizer()
    classifier = ContentClassifier()
    formatter = Formatter()

    # 1. Pipeline
    print("Running Pipeline...")
    doc = parser.parse(docx_path, "debug_job")
    doc = normalizer.process(doc)
    doc = classifier.process(doc)

    # 2. Render
    print("Rendering...")
    word_doc = formatter.format(doc, template_name="none")

    # 3. Inspect
    print(f"Generated Document Paragraphs: {len(word_doc.paragraphs)}")
    print(f"Generated Document Tables: {len(word_doc.tables)}")

    # Check for InlineShapes (images)
    inline_shapes = word_doc.inline_shapes
    print(f"Generated Document Inline Shapes: {len(inline_shapes)}")

    # 4. Save
    word_doc.save(out_path)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    docx_path = "uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx"
    out_path = "debug_output.docx"
    debug_render(docx_path, out_path)
