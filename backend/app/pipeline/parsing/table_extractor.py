# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Table Extractor — Microsoft Table Transformer for academic PDF tables.

Uses two specialized models:
  1. microsoft/table-transformer-detection     — detect table bounding boxes
  2. microsoft/table-transformer-structure-recognition — extract rows/columns

Falls back gracefully if dependencies are unavailable.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Tuple
from app.utils.singleton import get_or_create_catching

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Optional imports
# --------------------------------------------------------------------------- #
TABLE_TRANSFORMER_AVAILABLE = False
_load_error: Optional[str] = None

try:
    import torch
    from transformers import (
        AutoImageProcessor,
        TableTransformerForObjectDetection,
    )
    from PIL import Image

    TABLE_TRANSFORMER_AVAILABLE = True
except ImportError as exc:
    _load_error = str(exc)
    logger.info(
        "Table Transformer dependencies not installed (%s). "
        "Install with: pip install transformers torch timm Pillow",
        exc,
    )

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #
DETECTION_MODEL = "microsoft/table-transformer-detection"
STRUCTURE_MODEL = "microsoft/table-transformer-structure-recognition"

# DETR detection thresholds
TABLE_DETECTION_THRESHOLD = 0.7
STRUCTURE_DETECTION_THRESHOLD = 0.6


# --------------------------------------------------------------------------- #
#  Main class
# --------------------------------------------------------------------------- #
class TableExtractor:
    """
    Detects and extracts table structure from page images using
    Microsoft's Table Transformer models.

    Models are lazy-loaded on first use and cached in ModelStore.
    """

    def __init__(self):
        if not TABLE_TRANSFORMER_AVAILABLE:
            raise ImportError(
                f"Table Transformer unavailable: {_load_error}. "
                "Install with: pip install transformers torch timm Pillow"
            )
        self._detection_model = None
        self._detection_processor = None
        self._structure_model = None
        self._structure_processor = None
        self._device = None
        self._loaded = False

    # ------------------------------------------------------------------ #
    #  Lazy loading
    # ------------------------------------------------------------------ #
    def _ensure_loaded(self):
        """Load both models on first use."""
        if self._loaded:
            return

        from app.services.model_store import model_store

        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # --- Detection model --- #
        if model_store.is_loaded("table_detection_model"):
            self._detection_model = model_store.get_model("table_detection_model")
            self._detection_processor = model_store.get_model("table_detection_processor")
        else:
            logger.info("TableExtractor: Loading detection model '%s'...", DETECTION_MODEL)
            self._detection_processor = AutoImageProcessor.from_pretrained(DETECTION_MODEL)  # nosec
            self._detection_model = TableTransformerForObjectDetection.from_pretrained(
                DETECTION_MODEL  # nosec
            )
            self._detection_model.to(self._device)
            self._detection_model.eval()
            model_store.set_model("table_detection_model", self._detection_model)
            model_store.set_model("table_detection_processor", self._detection_processor)
            logger.info("TableExtractor: Detection model loaded on %s.", self._device)

        # --- Structure recognition model --- #
        if model_store.is_loaded("table_structure_model"):
            self._structure_model = model_store.get_model("table_structure_model")
            self._structure_processor = model_store.get_model("table_structure_processor")
        else:
            logger.info("TableExtractor: Loading structure model '%s'...", STRUCTURE_MODEL)
            self._structure_processor = AutoImageProcessor.from_pretrained(STRUCTURE_MODEL)  # nosec
            self._structure_model = TableTransformerForObjectDetection.from_pretrained(
                STRUCTURE_MODEL  # nosec
            )
            self._structure_model.to(self._device)
            self._structure_model.eval()
            model_store.set_model("table_structure_model", self._structure_model)
            model_store.set_model("table_structure_processor", self._structure_processor)
            logger.info("TableExtractor: Structure model loaded on %s.", self._device)

        self._loaded = True

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def detect_tables(
        self, image: "Image.Image", threshold: float = TABLE_DETECTION_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Detect table bounding boxes in a page image.

        Args:
            image: PIL Image of a PDF page.
            threshold: Minimum confidence score.

        Returns:
            List of dicts: [{"bbox": (x0, y0, x1, y1), "score": float}, ...]
        """
        self._ensure_loaded()

        inputs = self._detection_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._detection_model(**inputs)

        # Post-process results
        target_sizes = torch.tensor([image.size[::-1]]).to(self._device)
        results = self._detection_processor.post_process_object_detection(
            outputs, threshold=threshold, target_sizes=target_sizes
        )[0]

        tables = []
        for score, label, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            bbox = box.cpu().tolist()
            tables.append(
                {
                    "bbox": tuple(bbox),  # (x0, y0, x1, y1)
                    "score": round(score.item(), 4),
                    "label": self._detection_model.config.id2label.get(
                        label.item(), "table"
                    ),
                }
            )

        logger.info("TableExtractor: Detected %d tables in image.", len(tables))
        return tables

    def extract_table_structure(
        self,
        table_image: "Image.Image",
        threshold: float = STRUCTURE_DETECTION_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Recognize rows, columns, and cell structure within a cropped table image.

        Args:
            table_image: Cropped PIL Image of a single table.
            threshold: Minimum confidence score for structure elements.

        Returns:
            Dict with keys: "rows", "columns", "cells", "data"
        """
        self._ensure_loaded()

        inputs = self._structure_processor(images=table_image, return_tensors="pt")
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._structure_model(**inputs)

        target_sizes = torch.tensor([table_image.size[::-1]]).to(self._device)
        results = self._structure_processor.post_process_object_detection(
            outputs, threshold=threshold, target_sizes=target_sizes
        )[0]

        rows = []
        columns = []
        headers = []

        id2label = self._structure_model.config.id2label

        for score, label_id, box in zip(
            results["scores"], results["labels"], results["boxes"]
        ):
            label = id2label.get(label_id.item(), "unknown")
            bbox = box.cpu().tolist()
            entry = {"bbox": tuple(bbox), "score": round(score.item(), 4)}

            if label == "table row":
                rows.append(entry)
            elif label == "table column":
                columns.append(entry)
            elif label == "table column header":
                headers.append(entry)

        # Sort rows top-to-bottom, columns left-to-right
        rows.sort(key=lambda r: r["bbox"][1])
        columns.sort(key=lambda c: c["bbox"][0])

        # Build grid dimensions
        num_rows = len(rows)
        num_cols = len(columns)

        # Create empty data grid
        data: List[List[str]] = [["" for _ in range(max(num_cols, 1))] for _ in range(max(num_rows, 1))]

        return {
            "num_rows": num_rows,
            "num_cols": num_cols,
            "rows": rows,
            "columns": columns,
            "headers": headers,
            "data": data,
        }

    def extract_tables_from_page(
        self, page_image: "Image.Image"
    ) -> List[Dict[str, Any]]:
        """
        Full pipeline: detect tables in a page, then extract structure for each.

        Args:
            page_image: PIL Image of a full PDF page.

        Returns:
            List of table dicts, each with detection + structure info.
        """
        self._ensure_loaded()

        detections = self.detect_tables(page_image)
        results = []

        for det in detections:
            x0, y0, x1, y1 = det["bbox"]

            # Crop the table region
            table_crop = page_image.crop((int(x0), int(y0), int(x1), int(y1)))

            try:
                structure = self.extract_table_structure(table_crop)
            except Exception as exc:
                logger.warning("TableExtractor: Structure extraction failed: %s", exc)
                structure = {"num_rows": 0, "num_cols": 0, "rows": [], "columns": [], "headers": [], "data": []}

            results.append(
                {
                    "detection": det,
                    "structure": structure,
                }
            )

        return results

    def to_table_model(
        self,
        table_data: Dict[str, Any],
        table_index: int,
        block_index: int,
        page_number: Optional[int] = None,
    ) -> Any:
        """
        Convert extracted table data to the project's Table model.

        Args:
            table_data: Output from extract_tables_from_page (single item).
            table_index: Sequential index among all tables.
            block_index: Global block index in document order.
            page_number: Page where the table appears.

        Returns:
            Table model instance.
        """
        from app.models.table import Table, TableCell
        from app.utils.id_generator import generate_block_id

        structure = table_data.get("structure", {})
        num_rows = structure.get("num_rows", 0)
        num_cols = structure.get("num_cols", 0)
        data = structure.get("data", [])
        has_header = len(structure.get("headers", [])) > 0

        # Build cells
        cells = []
        for r_idx, row_data in enumerate(data):
            for c_idx, cell_text in enumerate(row_data):
                cells.append(
                    TableCell(
                        row=r_idx,
                        col=c_idx,
                        text=str(cell_text),
                        is_header=(r_idx == 0 and has_header),
                    )
                )

        table_id = f"tbl_{table_index:03d}"

        return Table(
            table_id=table_id,
            num_rows=num_rows,
            num_cols=num_cols,
            cells=cells,
            data=data,
            rows=data,
            has_header=has_header,
            has_header_row=has_header,
            header_rows=1 if has_header else 0,
            page_number=page_number,
            index=table_index,
            block_index=block_index,
            metadata={"extractor": "table-transformer", "detection_score": table_data.get("detection", {}).get("score", 0)},
        )


# --------------------------------------------------------------------------- #
#  Singleton
# --------------------------------------------------------------------------- #
_extractor: Optional[TableExtractor] = None


def get_table_extractor() -> Optional[TableExtractor]:
    """Get or create a TableExtractor instance. Returns None if unavailable."""
    global _extractor
    _extractor = get_or_create_catching(
        _extractor,
        TableExtractor,
        exceptions=(ImportError,),
    )
    return _extractor
