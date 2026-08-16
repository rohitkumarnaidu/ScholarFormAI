# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive tests for backend/app/pipeline/parsing/table_extractor.py.

Covers all public methods, lazy-loading paths, error branches, and the
singleton getter.  Targets 90%+ line / branch coverage.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

_torch_mock = MagicMock()
_torch_mock.cuda.is_available.return_value = False
_torch_mock.no_grad.return_value.__enter__.return_value = None
_torch_mock.no_grad.return_value.__exit__.return_value = None

_transformers_mock = MagicMock()
# Add the class to transformers mock so it doesn't raise AttributeError
_transformers_mock.TableTransformerForObjectDetection = MagicMock()
_transformers_mock.AutoImageProcessor = MagicMock()

_pil_mock = MagicMock()
_pil_image_mock = MagicMock()

for _mod_name, _mod_obj in [
    ("torch", _torch_mock),
    ("transformers", _transformers_mock),
]:
    sys.modules[_mod_name] = _mod_obj

import importlib.util

_original_find_spec = importlib.util.find_spec


def _mock_find_spec(name, package=None):
    if name in ["torch", "transformers"]:
        return MagicMock()
    return _original_find_spec(name, package=package)


importlib.util.find_spec = _mock_find_spec

import importlib

import app.pipeline.parsing.table_extractor

importlib.reload(app.pipeline.parsing.table_extractor)
app.pipeline.parsing.table_extractor.AutoImageProcessor = MagicMock()
app.pipeline.parsing.table_extractor.TableTransformerForObjectDetection = MagicMock()

from app.pipeline.parsing.table_extractor import (
    DETECTION_MODEL,
    STRUCTURE_DETECTION_THRESHOLD,
    STRUCTURE_MODEL,
    TABLE_DETECTION_THRESHOLD,
    TABLE_TRANSFORMER_AVAILABLE,
    TableExtractor,
    _load_error,
    get_table_extractor,
)

# ===================================================================
#  Helpers  — reduce duplication in test data construction
# ===================================================================


def _make_iter_mock(*values, item_attr: str = "item", box: bool = False):
    """Build a MagicMock that iterates over *values*, each exposing *item_attr*."""
    elements = []
    for v in values:
        el = MagicMock()
        getattr(el, item_attr).return_value = v
        if box:
            cpu = MagicMock()
            cpu.tolist.return_value = list(v)
            el.cpu.return_value = cpu
        elements.append(el)
    m = MagicMock()
    m.__iter__.return_value = iter(elements)
    return m


def build_detection_dict(
    scores=(0.95, 0.82),
    labels=(0, 0),
    boxes=((10, 20, 100, 200), (150, 50, 300, 180)),
):
    """Simulate the dict returned by post_process_object_detection[0]."""
    return {
        "scores": _make_iter_mock(*scores),
        "labels": _make_iter_mock(*labels),
        "boxes": _make_iter_mock(*boxes, box=True),
    }


def build_structure_dict(
    scores=(0.91, 0.88, 0.76),
    label_ids=(0, 1, 2),
    boxes=((5, 10, 95, 50), (10, 5, 60, 90), (10, 5, 60, 20)),
):
    """Simulate the dict returned by post_process_object_detection[0]
    for structure recognition."""
    return {
        "scores": _make_iter_mock(*scores),
        "labels": _make_iter_mock(*label_ids),
        "boxes": _make_iter_mock(*boxes, box=True),
    }


# ===================================================================
#  Shared fixtures
# ===================================================================


@pytest.fixture
def image_mock():
    """Minimal PIL Image stand-in with a known .size."""
    img = MagicMock()
    img.size = (800, 600)
    return img


@pytest.fixture
def extractor():
    """Pre-loaded TableExtractor with mocked internals.  Ready to call
    detect_tables / extract_table_structure / extract_tables_from_page."""
    ext = TableExtractor.__new__(TableExtractor)
    ext._loaded = True
    ext._device = MagicMock()

    ext._detection_processor = MagicMock()
    ext._detection_model = MagicMock()
    ext._detection_model.config.id2label = {0: "table"}

    ext._structure_processor = MagicMock()
    ext._structure_model = MagicMock()
    ext._structure_model.config.id2label = {
        0: "table row",
        1: "table column",
        2: "table column header",
    }

    return ext


# ===================================================================
#  Module-level constants
# ===================================================================


class TestModuleConstants:
    def test_detection_model_name(self):
        assert DETECTION_MODEL == "microsoft/table-transformer-detection"

    def test_structure_model_name(self):
        assert STRUCTURE_MODEL == "microsoft/table-transformer-structure-recognition"

    def test_detection_threshold(self):
        assert TABLE_DETECTION_THRESHOLD == 0.7

    def test_structure_threshold(self):
        assert STRUCTURE_DETECTION_THRESHOLD == 0.6

    def test_table_transformer_flag_true(self):
        assert TABLE_TRANSFORMER_AVAILABLE is True

    def test_load_error_is_none(self):
        assert _load_error is None


# ===================================================================
#  Constructor (__init__)
# ===================================================================


class TestInit:
    def test_sets_initial_state(self):
        ext = TableExtractor()
        assert ext._detection_model is None
        assert ext._detection_processor is None
        assert ext._structure_model is None
        assert ext._structure_processor is None
        assert ext._device is None
        assert ext._loaded is False

    @patch("app.pipeline.parsing.table_extractor.TABLE_TRANSFORMER_AVAILABLE", False)
    @patch("app.pipeline.parsing.table_extractor._load_error", "stub: no torch")
    def test_raises_import_error_when_unavailable(self):
        with pytest.raises(ImportError) as exc:
            TableExtractor()
        msg = str(exc.value)
        assert "Table Transformer unavailable" in msg
        assert "stub: no torch" in msg


# ===================================================================
#  Lazy loading (_ensure_loaded)
# ===================================================================


class TestEnsureLoaded:
    """Exercises all four code paths inside _ensure_loaded."""

    @patch("app.services.model_store.model_store")
    @patch("transformers.AutoImageProcessor.from_pretrained")
    @patch("transformers.TableTransformerForObjectDetection.from_pretrained")
    def test_loads_both_from_scratch(self, mock_ttod_fp, mock_aip_fp, mock_ms):
        mock_ms.is_loaded.return_value = False
        mock_aip_fp.return_value = MagicMock()
        mock_ttod_fp.return_value = det_model = MagicMock()
        det_model.to.return_value = det_model

        ext = TableExtractor()
        ext._ensure_loaded()

        assert ext._loaded is True
        mock_aip_fp.assert_any_call(DETECTION_MODEL)
        mock_aip_fp.assert_any_call(STRUCTURE_MODEL)
        assert mock_ttod_fp.call_count == 2
        assert mock_ms.set_model.call_count == 4

    @patch("app.services.model_store.model_store")
    @patch("transformers.AutoImageProcessor.from_pretrained")
    @patch("transformers.TableTransformerForObjectDetection.from_pretrained")
    def test_detection_cached_structure_loaded(self, mock_ttod_fp, mock_aip_fp, mock_ms):
        def is_loaded(key):
            return key == "table_detection_model"

        mock_ms.is_loaded.side_effect = is_loaded
        mock_ms.get_model.side_effect = lambda k: (
            MagicMock() if k in ("table_detection_model", "table_detection_processor") else None
        )
        mock_aip_fp.return_value = MagicMock()
        mock_ttod_fp.return_value = MagicMock()
        mock_ttod_fp.return_value.to.return_value = MagicMock()

        ext = TableExtractor()
        ext._ensure_loaded()

        assert ext._loaded is True
        assert ext._detection_model is not None
        assert ext._detection_processor is not None
        # Structure model should be loaded from pretrained
        mock_aip_fp.assert_called_once_with(STRUCTURE_MODEL)
        mock_ttod_fp.assert_called_once_with(STRUCTURE_MODEL)

    @patch("app.services.model_store.model_store")
    @patch("transformers.AutoImageProcessor.from_pretrained")
    @patch("transformers.TableTransformerForObjectDetection.from_pretrained")
    def test_structure_cached_detection_loaded(self, mock_ttod_fp, mock_aip_fp, mock_ms):
        def is_loaded(key):
            return key == "table_structure_model"

        mock_ms.is_loaded.side_effect = is_loaded
        mock_ms.get_model.side_effect = lambda k: (
            MagicMock() if k in ("table_structure_model", "table_structure_processor") else None
        )
        mock_aip_fp.return_value = MagicMock()
        mock_ttod_fp.return_value = MagicMock()
        mock_ttod_fp.return_value.to.return_value = MagicMock()

        ext = TableExtractor()
        ext._ensure_loaded()

        assert ext._loaded is True
        assert ext._structure_model is not None
        assert ext._structure_processor is not None
        # Detection model should be loaded from pretrained
        mock_aip_fp.assert_called_once_with(DETECTION_MODEL)
        mock_ttod_fp.assert_called_once_with(DETECTION_MODEL)

    @patch("app.services.model_store.model_store")
    def test_both_cached(self, mock_ms):
        mock_ms.is_loaded.return_value = True
        mock_ms.get_model.return_value = MagicMock()

        ext = TableExtractor()
        ext._ensure_loaded()

        assert ext._loaded is True
        assert ext._detection_model is not None
        assert ext._detection_processor is not None
        assert ext._structure_model is not None
        assert ext._structure_processor is not None

    def test_already_loaded_returns_early(self):
        ext = TableExtractor.__new__(TableExtractor)
        ext._loaded = True
        # No crash / no model-store interaction expected
        ext._ensure_loaded()
        assert ext._loaded is True


# ===================================================================
#  detect_tables
# ===================================================================


class TestDetectTables:
    @pytest.fixture(autouse=True)
    def _wire_mocks(self, extractor, image_mock):
        self.ext = extractor
        self.img = image_mock

    def _setup_detection(self, detection_dict):
        self.ext._detection_processor.return_value = {"pixel_values": MagicMock()}
        self.ext._detection_processor.post_process_object_detection.return_value = [detection_dict]

    def test_multiple_tables_returned(self):
        det = build_detection_dict(
            scores=(0.95, 0.82),
            labels=(0, 0),
            boxes=((10, 20, 100, 200), (150, 50, 300, 180)),
        )
        self._setup_detection(det)
        self.ext._detection_model.config.id2label = {0: "table"}

        result = self.ext.detect_tables(self.img)

        assert len(result) == 2
        assert result[0]["bbox"] == (10, 20, 100, 200)
        assert result[0]["score"] == 0.95
        assert result[0]["label"] == "table"
        assert result[1]["bbox"] == (150, 50, 300, 180)
        assert result[1]["score"] == 0.82

    def test_custom_threshold_passed_through(self):
        det = build_detection_dict(scores=(0.65,), labels=(0,), boxes=((0, 0, 50, 50),))
        self._setup_detection(det)

        self.ext.detect_tables(self.img, threshold=0.6)

        args, kwargs = self.ext._detection_processor.post_process_object_detection.call_args
        assert kwargs["threshold"] == 0.6

    def test_unknown_label_falls_back(self):
        det = build_detection_dict(scores=(0.90,), labels=(99,), boxes=((5, 5, 50, 50),))
        self._setup_detection(det)
        self.ext._detection_model.config.id2label = {}

        result = self.ext.detect_tables(self.img)

        assert result[0]["label"] == "table"

    def test_empty_result_when_no_tables(self):
        det = build_detection_dict(scores=(), labels=(), boxes=())
        self._setup_detection(det)

        result = self.ext.detect_tables(self.img)

        assert result == []


# ===================================================================
#  extract_table_structure
# ===================================================================


class TestExtractTableStructure:
    @pytest.fixture(autouse=True)
    def _wire_mocks(self, extractor, image_mock):
        self.ext = extractor
        self.img = image_mock

    def _setup_structure(self, structure_dict):
        self.ext._structure_processor.return_value = {"pixel_values": MagicMock()}
        self.ext._structure_processor.post_process_object_detection.return_value = [structure_dict]

    def test_rows_columns_and_headers(self):
        # label ids: 0=row, 1=column, 2=header
        struct = build_structure_dict(
            scores=(0.91, 0.88, 0.76),
            label_ids=(0, 1, 2),
            boxes=((5, 10, 95, 50), (10, 5, 60, 90), (10, 5, 60, 20)),
        )
        self._setup_structure(struct)

        result = self.ext.extract_table_structure(self.img)

        assert result["num_rows"] == 1
        assert result["num_cols"] == 1
        assert len(result["rows"]) == 1
        assert len(result["columns"]) == 1
        assert len(result["headers"]) == 1
        assert result["data"] == [[""]]

    def test_multiple_rows_and_columns_sorted(self):
        struct = build_structure_dict(
            scores=(0.9, 0.9, 0.9, 0.9),
            label_ids=(0, 0, 1, 1),
            boxes=((5, 30, 95, 60), (5, 10, 95, 30), (10, 5, 40, 90), (50, 5, 90, 90)),
        )
        self._setup_structure(struct)

        result = self.ext.extract_table_structure(self.img)

        assert result["num_rows"] == 2
        assert result["num_cols"] == 2
        # Rows sorted by y1 (bbox[1]) → first is (5, 10, ...), second is (5, 30, ...)
        assert result["rows"][0]["bbox"][1] == 10
        assert result["rows"][1]["bbox"][1] == 30
        # Columns sorted by x0 (bbox[0]) → first is (10, ...), second is (50, ...)
        assert result["columns"][0]["bbox"][0] == 10
        assert result["columns"][1]["bbox"][0] == 50

    def test_no_rows_or_columns(self):
        struct = build_structure_dict(scores=(), label_ids=(), boxes=())
        self._setup_structure(struct)

        result = self.ext.extract_table_structure(self.img)

        assert result["num_rows"] == 0
        assert result["num_cols"] == 0
        # data should be 1x1 because of max(0, 1)
        assert result["data"] == [[""]]

    def test_custom_threshold(self):
        struct = build_structure_dict(scores=(0.5,), label_ids=(0,), boxes=((0, 0, 50, 50),))
        self._setup_structure(struct)

        self.ext.extract_table_structure(self.img, threshold=0.4)

        args, kwargs = self.ext._structure_processor.post_process_object_detection.call_args
        assert kwargs["threshold"] == 0.4

    def test_unknown_label_skipped(self):
        struct = build_structure_dict(scores=(0.9,), label_ids=(42,), boxes=((0, 0, 10, 10),))
        self._setup_structure(struct)
        self.ext._structure_model.config.id2label = {42: "garbage"}

        result = self.ext.extract_table_structure(self.img)

        assert result["num_rows"] == 0
        assert result["num_cols"] == 0
        assert len(result["rows"]) == 0
        assert len(result["columns"]) == 0
        assert len(result["headers"]) == 0


# ===================================================================
#  extract_tables_from_page  (full pipeline)
# ===================================================================


class TestExtractTablesFromPage:
    @pytest.fixture(autouse=True)
    def _wire_mocks(self, extractor, image_mock):
        self.ext = extractor
        self.img = image_mock

    def test_happy_path_multiple_tables(self):
        detections = [
            {"bbox": (10, 20, 100, 200), "score": 0.95, "label": "table"},
            {"bbox": (150, 50, 300, 180), "score": 0.82, "label": "table"},
        ]
        self.ext.detect_tables = MagicMock(return_value=detections)

        structure_1 = {
            "num_rows": 2,
            "num_cols": 2,
            "rows": [{"bbox": (0, 0, 90, 30), "score": 0.9}],
            "columns": [{"bbox": (0, 0, 45, 180), "score": 0.9}],
            "headers": [],
            "data": [["a", "b"], ["c", "d"]],
        }
        structure_2 = {
            "num_rows": 1,
            "num_cols": 3,
            "rows": [],
            "columns": [],
            "headers": [],
            "data": [["x", "y", "z"]],
        }
        self.ext.extract_table_structure = MagicMock(side_effect=[structure_1, structure_2])

        result = self.ext.extract_tables_from_page(self.img)

        assert len(result) == 2
        assert result[0]["detection"] == detections[0]
        assert result[0]["structure"] == structure_1
        assert result[1]["detection"] == detections[1]
        assert result[1]["structure"] == structure_2
        # Verify cropping was called for each detection
        assert self.img.crop.call_count == 2

    def test_no_tables_detected(self):
        self.ext.detect_tables = MagicMock(return_value=[])

        result = self.ext.extract_tables_from_page(self.img)

        assert result == []

    def test_structure_extraction_fallback_on_error(self):
        detections = [
            {"bbox": (0, 0, 50, 50), "score": 0.9, "label": "table"},
        ]
        self.ext.detect_tables = MagicMock(return_value=detections)
        self.ext.extract_table_structure = MagicMock(side_effect=ValueError("crop failed"))

        result = self.ext.extract_tables_from_page(self.img)

        assert len(result) == 1
        empty = result[0]["structure"]
        assert empty["num_rows"] == 0
        assert empty["num_cols"] == 0
        assert empty["rows"] == []
        assert empty["columns"] == []
        assert empty["headers"] == []
        assert empty["data"] == []

    def test_mixed_success_and_failure(self):
        detections = [
            {"bbox": (0, 0, 50, 50), "score": 0.9, "label": "table"},
            {"bbox": (60, 0, 100, 50), "score": 0.8, "label": "table"},
        ]
        good_structure = {
            "num_rows": 1,
            "num_cols": 1,
            "rows": [],
            "columns": [],
            "headers": [],
            "data": [["ok"]],
        }
        self.ext.detect_tables = MagicMock(return_value=detections)
        self.ext.extract_table_structure = MagicMock(side_effect=[good_structure, RuntimeError("OOM")])

        result = self.ext.extract_tables_from_page(self.img)

        assert len(result) == 2
        assert result[0]["structure"] == good_structure
        assert result[1]["structure"]["num_rows"] == 0


# ===================================================================
#  to_table_model
# ===================================================================


class TestToTableModel:
    def _make_table_data(self, detection=None, structure=None):
        return {
            "detection": detection or {"bbox": (0, 0, 100, 100), "score": 0.95, "label": "table"},
            "structure": structure
            or {
                "num_rows": 2,
                "num_cols": 3,
                "rows": [],
                "columns": [],
                "headers": [],
                "data": [["a", "b", "c"], ["d", "e", "f"]],
            },
        }

    @patch("app.utils.id_generator.generate_block_id", return_value="blk_000")
    def test_without_headers(self, mock_gid, extractor):
        table_data = self._make_table_data()
        result = extractor.to_table_model(table_data, table_index=0, block_index=0)

        assert result.table_id == "tbl_000"
        assert result.num_rows == 2
        assert result.num_cols == 3
        assert result.data == [["a", "b", "c"], ["d", "e", "f"]]
        assert result.rows == [["a", "b", "c"], ["d", "e", "f"]]
        assert result.has_header is False
        assert result.has_header_row is False
        assert result.header_rows == 0
        assert result.index == 0
        assert result.block_index == 0
        assert result.page_number is None
        # No cell should be marked as header
        for cell in result.cells:
            assert cell.is_header is False

    @patch("app.utils.id_generator.generate_block_id", return_value="blk_001")
    def test_with_headers(self, mock_gid, extractor):
        table_data = self._make_table_data(
            structure={
                "num_rows": 2,
                "num_cols": 2,
                "rows": [],
                "columns": [],
                "headers": [{"bbox": (0, 0, 50, 10), "score": 0.9}],
                "data": [["Name", "Value"], ["Temp", "42"]],
            }
        )
        result = extractor.to_table_model(table_data, table_index=1, block_index=5, page_number=2)

        assert result.table_id == "tbl_001"
        assert result.has_header is True
        assert result.has_header_row is True
        assert result.header_rows == 1
        assert result.page_number == 2
        assert result.block_index == 5
        assert result.index == 1
        # Row 0 cells are headers
        assert result.cells[0].is_header is True
        assert result.cells[1].is_header is True
        # Row 1 cells are not headers
        assert result.cells[2].is_header is False
        assert result.cells[3].is_header is False

    @patch("app.utils.id_generator.generate_block_id", return_value="blk_002")
    def test_empty_data_grid(self, mock_gid, extractor):
        table_data = self._make_table_data(
            structure={
                "num_rows": 0,
                "num_cols": 0,
                "rows": [],
                "columns": [],
                "headers": [],
                "data": [],
            }
        )
        result = extractor.to_table_model(table_data, table_index=2, block_index=10)

        assert result.table_id == "tbl_002"
        assert result.num_rows == 0
        assert result.num_cols == 0
        assert result.data == []
        assert result.cells == []
        assert result.has_header is False
        assert result.header_rows == 0

    @patch("app.utils.id_generator.generate_block_id", return_value="blk_003")
    def test_metadata_contains_detection_score(self, mock_gid, extractor):
        table_data = self._make_table_data(detection={"bbox": (0, 0, 50, 50), "score": 0.9876, "label": "table"})
        result = extractor.to_table_model(table_data, table_index=3, block_index=15)

        meta = result.metadata
        assert meta["extractor"] == "table-transformer"
        assert meta["detection_score"] == 0.9876

    @patch("app.utils.id_generator.generate_block_id", return_value="blk_004")
    def test_missing_structure_keys_defaults(self, mock_gid, extractor):
        table_data = {
            "detection": {"bbox": (0, 0, 50, 50), "score": 0.9, "label": "table"},
            "structure": {},
        }
        result = extractor.to_table_model(table_data, table_index=4, block_index=20)

        assert result.num_rows == 0
        assert result.num_cols == 0
        assert result.data == []
        assert result.cells == []
        assert result.has_header is False


# ===================================================================
#  get_table_extractor  (singleton getter)
# ===================================================================


class TestGetTableExtractor:
    def teardown_method(self):
        """Reset the module-level _extractor global between tests."""
        import app.pipeline.parsing.table_extractor as te

        te._extractor = None

    @patch(
        "app.pipeline.parsing.table_extractor.get_or_create_catching",
        return_value=MagicMock(spec=TableExtractor),
    )
    def test_returns_instance(self, mock_goc):
        instance = get_table_extractor()
        assert instance is not None
        assert isinstance(instance, MagicMock)

    @patch(
        "app.pipeline.parsing.table_extractor.get_or_create_catching",
        return_value=None,
    )
    def test_returns_none_on_import_error(self, mock_goc):
        result = get_table_extractor()
        assert result is None

    def test_singleton_global_is_updated(self):
        """Calling get_table_extractor sets the module-level _extractor."""
        import app.pipeline.parsing.table_extractor as te

        te._extractor = None
        # Provide a real extractor so we can verify identity
        with patch(
            "app.pipeline.parsing.table_extractor.get_or_create_catching",
            return_value="cached-instance",
        ):
            instance = get_table_extractor()
            assert te._extractor == "cached-instance"
            assert instance == "cached-instance"


# ===================================================================
#  Edge: detect_tables called without _ensure_loaded being a no-op
# ===================================================================


class TestDetectTablesLazyLoading:
    """Verify that detect_tables / extract_table_structure trigger
    _ensure_loaded when called on a fresh extractor."""

    def test_detect_tables_triggers_ensure_loaded(self, image_mock):
        """
        Even if _loaded is False, detect_tables should work once we mock the
        internal chain after _ensure_loaded completes.
        """
        det = build_detection_dict(scores=(0.9,), labels=(0,), boxes=((0, 0, 50, 50),))

        ext = TableExtractor.__new__(TableExtractor)
        ext._loaded = False
        ext._device = MagicMock()
        ext._detection_processor = MagicMock()
        ext._detection_processor.return_value = {"px": MagicMock()}
        ext._detection_processor.post_process_object_detection.return_value = [det]
        ext._detection_model = MagicMock()
        ext._detection_model.config.id2label = {0: "table"}

        # Patch _ensure_loaded to just set _loaded = True

        def fake_ensure():
            ext._loaded = True
            ext._device = MagicMock()

        ext._ensure_loaded = fake_ensure

        result = ext.detect_tables(image_mock)
        assert len(result) == 1
        assert ext._loaded is True


# ===================================================================
#  Edge: extract_table_structure on non-loaded extractor
# ===================================================================


class TestExtractStructureLazyLoading:
    def test_extract_structure_triggers_ensure_loaded(self, image_mock):
        struct = build_structure_dict(
            scores=(0.9, 0.8),
            label_ids=(0, 1),
            boxes=((0, 0, 50, 50), (0, 0, 50, 50)),
        )

        ext = TableExtractor.__new__(TableExtractor)
        ext._loaded = False
        ext._device = MagicMock()
        ext._structure_processor = MagicMock()
        ext._structure_processor.return_value = {"px": MagicMock()}
        ext._structure_processor.post_process_object_detection.return_value = [struct]
        ext._structure_model = MagicMock()
        ext._structure_model.config.id2label = {0: "table row", 1: "table column"}

        def fake_ensure():
            ext._loaded = True
            ext._device = MagicMock()

        ext._ensure_loaded = fake_ensure

        result = ext.extract_table_structure(image_mock)
        assert result["num_rows"] == 1
        assert result["num_cols"] == 1
