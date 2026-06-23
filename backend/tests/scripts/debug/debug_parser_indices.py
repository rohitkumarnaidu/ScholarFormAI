# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
import os
from app.pipeline.parsing.parser import DocxParser
from app.models.pipeline_document import PipelineDocument

def debug_indices(docx_path):
    parser = DocxParser()
    try:
        doc = parser.parse(docx_path, "debug_job")
        print(f"Parser extracted {len(doc.blocks)} blocks and {len(doc.tables)} tables.")
        
        block_indices = [b.index for b in doc.blocks]
        table_indices = [t.block_index for t in doc.tables]
        
        all_indices = block_indices + [idx for idx in table_indices if idx is not None]
        duplicates = [idx for idx in all_indices if all_indices.count(idx) > 1]
        
        if duplicates:
            print(f"CRITICAL: Parser generated duplicate indices: {set(duplicates)}")
        else:
            print("Parser indices are unique.")
            
        # Check Figures
        print(f"Figures: {len(doc.figures)}")
        for i, fig in enumerate(doc.figures):
            print(f"  Fig {i}: block_index={fig.metadata.get('block_index')}, figure_id={fig.figure_id}")
            
    except Exception as e:
        print(f"Error during parsing: {e}")

if __name__ == "__main__":
    docx_path = "uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx"
    debug_indices(docx_path)
