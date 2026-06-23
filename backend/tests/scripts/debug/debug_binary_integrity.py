# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


import sys
import os
from app.pipeline.parsing.parser import DocxParser
from app.models.pipeline_document import PipelineDocument

def verify_binary_data(docx_path):
    parser = DocxParser()
    try:
        doc = parser.parse(docx_path, "debug_job")
        print(f"--- Extraction Audit ---")
        print(f"Blocks: {len(doc.blocks)}")
        print(f"Figures: {len(doc.figures)}")
        print(f"Tables: {len(doc.tables)}")
        
        for i, fig in enumerate(doc.figures):
            has_data = fig.image_data is not None and len(fig.image_data) > 0
            size = len(fig.image_data) if fig.image_data else 0
            print(f"Fig {i} ({fig.figure_id}): has_data={has_data}, size={size} bytes, format={fig.image_format}")
            print(f"  block_index: {fig.metadata.get('block_index')}")
            
        for i, tbl in enumerate(doc.tables):
            has_rows = hasattr(tbl, 'rows') and tbl.rows is not None and len(tbl.rows) > 0
            row_count = len(tbl.rows) if has_rows else 0
            print(f"Tbl {i} ({tbl.table_id}): has_rows={has_rows}, rows={row_count}, index={tbl.index}, block_index={tbl.block_index}")
            if has_rows:
                print(f"  First row: {tbl.rows[0]}")
                
    except Exception as e:
        print(f"Error during parsing: {e}")

if __name__ == "__main__":
    docx_path = "uploads/132dbdae-b6e3-4936-bdb5-bc398ed0ac19.docx"
    verify_binary_data(docx_path)
