# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Table Extractor - Production Grade Stage 3 Component.
Handles extraction of structured data from docx Table objects.
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)
from docx.table import Table as DocxTable
from app.models.table import Table, TableCell


class TableExtractor:
    """
    Production-safe, deterministic table data extractor.

    Responsibilities:
    - Extract full cell matrix in List[List[str]] format.
    - Normalize whitespace and preserve internal line breaks.
    - Detect header rows based on visual cues (bold) and context.
    - Accurately set dimensions (num_rows, num_cols).
    """

    def extract(self, docx_table: DocxTable, table_id: str, index: int, block_index: int) -> Table:
        """
        Extract a structured Table model with a guaranteed 2D data matrix.
        """
        raw_data: List[List[str]] = []
        max_cols = 0

        # 1. Primary extraction phase
        for row in docx_table.rows:
            row_cells_text = []
            for cell in row.cells:
                # Standard extraction
                clean_text = cell.text.strip()

                # Deep fallback (Stage 3 Production Grade)
                if not clean_text:
                    try:
                        deep_text = self._extract_deep_xml_text(cell)
                        if deep_text:
                            logger.debug("Fixed empty cell via deep extraction: '%s'", deep_text[:20])
                            clean_text = deep_text
                    except Exception as exc:
                        logger.debug("Deep XML extraction failed for cell: %s", exc)

                row_cells_text.append(clean_text)

            raw_data.append(row_cells_text)
            max_cols = max(max_cols, len(row_cells_text))

        # 2. Normalization phase (Strict Production Grade)
        # Ensure all rows have equal length (num_cols)
        for row_list in raw_data:
            while len(row_list) < max_cols:
                row_list.append("")

        num_rows = len(raw_data)
        num_cols = max_cols

        # 3. Create structured cell objects for model completeness
        cells: List[TableCell] = []
        has_header = False
        row_has_bold_first = False

        for r_idx, row_text_list in enumerate(raw_data):
            for c_idx, text in enumerate(row_text_list):
                # Try to get the original cell for formatting hints and children
                original_cell = docx_table.rows[r_idx].cells[c_idx]

                is_bold = self._is_cell_bold(original_cell)
                if is_bold and r_idx == 0:
                    row_has_bold_first = True

                cell_obj = TableCell(row=r_idx, col=c_idx, text=text, bold=is_bold)

                # RECURSIVE EXTRACTION: Check for nested tables
                nested_tables = []
                try:
                    from docx.oxml.ns import qn

                    for tbl_xml in original_cell._element.findall(qn("w:tbl")):
                        from docx.table import Table as DocxTableWrapper

                        doc_parent = original_cell._parent._parent._parent
                        nested_tbl_id = f"{table_id}_n{len(nested_tables)}"
                        nested_docx_tbl = DocxTableWrapper(tbl_xml, doc_parent)
                        nested_table = self.extract(
                            nested_docx_tbl,
                            nested_tbl_id,
                            index=index + len(nested_tables) + 1,
                            block_index=block_index + len(nested_tables) + 1,
                        )
                        nested_tables.append(nested_table)
                except Exception as exc:
                    logger.warning("Nested table extraction failed for cell (%d,%d): %s", r_idx, c_idx, exc)

                if nested_tables:
                    cell_obj.metadata["nested_tables"] = nested_tables

                cells.append(cell_obj)

            # Header detection
            if r_idx == 0:
                if row_has_bold_first or self._contains_header_keywords(row_text_list):
                    has_header = True

        # Validation logging
        logger.debug(
            "Table '%s' extracted: %dx%d, nested=%d, sample=%s",
            table_id,
            num_rows,
            num_cols,
            sum(len(c.metadata.get("nested_tables", [])) for c in cells),
            raw_data[0][:3] if raw_data else [],
        )

        # 4. Final Table assembly
        extracted_table = Table(
            table_id=table_id,
            index=index,
            block_index=block_index,
            num_rows=num_rows,
            num_cols=num_cols,
            cells=cells,
            data=raw_data,
            rows=raw_data,  # Legacy support
            has_header=has_header,
            has_header_row=has_header,
            header_rows=1 if has_header else 0,
        )

        return extracted_table

    def _normalize_cell_text(self, text: str) -> str:
        """Strip exterior whitespace but keep internal structure."""
        if not text:
            return ""
        return text.strip()

    def _extract_deep_xml_text(self, cell) -> str:
        """
        Deep-scan raw XML for any hidden text nodes.
        Useful for tables with complex formatting or content controls.
        """
        text_parts = []
        try:
            for node in cell._tc.iter():
                if node.tag.endswith("}t") and node.text:
                    text_parts.append(node.text)
            return "".join(text_parts).strip()
        except Exception as exc:
            logger.debug("Deep XML text extraction error: %s", exc)
            return ""

    def _is_cell_bold(self, cell) -> bool:
        """Check if any run in the cell is bold."""
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                if run.bold:
                    return True
        return False

    def _contains_header_keywords(self, row_data: List[str]) -> bool:
        """Simple rule-based check for header-like content."""
        common_headers = {"id", "no.", "name", "date", "description", "value", "parameter", "result", "status", "type"}
        match_count = 0
        for text in row_data:
            lower_text = text.lower().strip()
            if lower_text in common_headers or any(h in lower_text for h in ["unit", "qty", "amount"]):
                match_count += 1
        return match_count > 0
