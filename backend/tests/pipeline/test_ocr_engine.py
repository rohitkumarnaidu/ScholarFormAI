# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Comprehensive tests for the OCR Engine module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.parsing import ocr_engine as ocr_module
from app.pipeline.parsing.ocr_engine import OCREngine, get_ocr_engine


_sentinel = object()


# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the module-level singleton before each test."""
    ocr_module._ocr_engine = None


@pytest.fixture
def surya_available():
    """Make Surya appear available by setting stubs directly on the module."""
    surya_names = [
        "run_ocr", "batch_text_detection", "batch_layout_detection",
        "batch_ordering", "load_det_model", "load_det_processor",
        "load_rec_model", "load_rec_processor", "load_order_model",
        "load_order_processor",
    ]
    saved = {}
    for name in surya_names:
        saved[name] = ocr_module.__dict__.pop(name, _sentinel)
        setattr(ocr_module, name, MagicMock())

    saved_surya = ocr_module.SURYA_AVAILABLE
    ocr_module.SURYA_AVAILABLE = True

    yield

    ocr_module.SURYA_AVAILABLE = saved_surya
    for name in surya_names:
        ocr_module.__dict__.pop(name, None)
        if saved[name] is not _sentinel:
            ocr_module.__dict__[name] = saved[name]


@pytest.fixture
def model_store():
    """Mock the model_store singleton from app.services.model_store."""
    with patch("app.services.model_store.model_store") as mock:
        mock.is_loaded.return_value = False
        yield mock


# --------------------------------------------------------------------------- #
#  Helper factories
# --------------------------------------------------------------------------- #

def _make_text_line(text="hello", confidence=0.95, bbox=None):
    line = MagicMock()
    line.text = text
    line.confidence = confidence
    line.bbox = bbox or [0, 0, 100, 20]
    return line


def _make_page_result(text_lines=None):
    page = MagicMock()
    page.text_lines = text_lines or [_make_text_line()]
    return page


def _make_region(label="Text", bbox=None, confidence=0.9):
    region = MagicMock()
    region.label = label
    region.bbox = bbox or [0, 0, 100, 50]
    if confidence is not None:
        region.confidence = confidence
    return region


def _make_layout_page(regions=None):
    page = MagicMock()
    page.bboxes = regions or [_make_region()]
    return page


def _make_order_item(position=0, bbox=None, label="text"):
    item = MagicMock()
    item.position = position
    item.bbox = bbox or [0, 0, 100, 50]
    if label is not None:
        item.label = label
    return item


def _make_order_page(items=None):
    page = MagicMock()
    page.bboxes = items or [_make_order_item()]
    return page


# --------------------------------------------------------------------------- #
#  Module-level defaults
# --------------------------------------------------------------------------- #

class TestModuleDefaults:
    """Verify module-level constants when Surya is absent."""

    def test_surya_available_false(self):
        assert ocr_module.SURYA_AVAILABLE is False

    def test_load_error_is_set(self):
        assert ocr_module._load_error is not None

    def test_ocr_engine_raises_import_error(self):
        with pytest.raises(ImportError, match="Surya OCR unavailable"):
            OCREngine()

    def test_get_ocr_engine_returns_none(self):
        assert get_ocr_engine() is None


# --------------------------------------------------------------------------- #
#  Construction & singleton (Surya available)
# --------------------------------------------------------------------------- #

class TestConstruction:
    """OCREngine creation when Surya is mocked as available."""

    def test_constructor_success(self, surya_available):
        engine = OCREngine()
        assert isinstance(engine, OCREngine)
        assert engine._loaded_det is False
        assert engine._loaded_rec is False
        assert engine._loaded_order is False
        assert engine._det_model is None
        assert engine._rec_model is None
        assert engine._order_model is None

    def test_get_ocr_engine_returns_instance(self, surya_available):
        engine = get_ocr_engine()
        assert isinstance(engine, OCREngine)

    def test_get_ocr_engine_caches(self, surya_available):
        e1 = get_ocr_engine()
        e2 = get_ocr_engine()
        assert e1 is e2


# --------------------------------------------------------------------------- #
#  Lazy model loading
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "flag_attr,method,"
    "load_model_attr,load_proc_attr,"
    "model_key,proc_key,"
    "attr_model,attr_proc",
    [
        ("_loaded_det", OCREngine._ensure_detection_loaded,
         "load_det_model", "load_det_processor",
         "surya_det_model", "surya_det_processor",
         "_det_model", "_det_processor"),
        ("_loaded_rec", OCREngine._ensure_recognition_loaded,
         "load_rec_model", "load_rec_processor",
         "surya_rec_model", "surya_rec_processor",
         "_rec_model", "_rec_processor"),
        ("_loaded_order", OCREngine._ensure_ordering_loaded,
         "load_order_model", "load_order_processor",
         "surya_order_model", "surya_order_processor",
         "_order_model", "_order_processor"),
    ],
)
class TestLazyLoading:
    """_ensure_*_loaded methods: from-store, fresh, and already-loaded paths."""

    # -- Already loaded (early return) ----------------------------------- #

    def test_already_loaded(self, surya_available, model_store,
                            flag_attr, method,
                            load_model_attr, load_proc_attr,
                            model_key, proc_key,
                            attr_model, attr_proc):
        engine = OCREngine()
        setattr(engine, flag_attr, True)
        method(engine)
        model_store.is_loaded.assert_not_called()

    # -- Load from store ------------------------------------------------- #

    def test_load_from_store(self, surya_available, model_store,
                             flag_attr, method,
                             load_model_attr, load_proc_attr,
                             model_key, proc_key,
                             attr_model, attr_proc):
        fake_model = MagicMock(name=f"cached_{model_key}")
        fake_proc = MagicMock(name=f"cached_{proc_key}")
        model_store.is_loaded.return_value = True
        model_store.get_model.side_effect = lambda k: {
            model_key: fake_model,
            proc_key: fake_proc,
        }[k]

        engine = OCREngine()
        method(engine)

        assert getattr(engine, attr_model) is fake_model
        assert getattr(engine, attr_proc) is fake_proc
        model_store.set_model.assert_not_called()

    # -- Load fresh ------------------------------------------------------ #

    def test_load_fresh(self, surya_available, model_store,
                        flag_attr, method,
                        load_model_attr, load_proc_attr,
                        model_key, proc_key,
                        attr_model, attr_proc):
        fake_model = MagicMock(name=f"fresh_{model_key}")
        fake_proc = MagicMock(name=f"fresh_{proc_key}")
        load_model_fn = getattr(ocr_module, load_model_attr)
        load_proc_fn = getattr(ocr_module, load_proc_attr)
        load_model_fn.return_value = fake_model
        load_proc_fn.return_value = fake_proc

        engine = OCREngine()
        method(engine)

        assert getattr(engine, attr_model) is fake_model
        assert getattr(engine, attr_proc) is fake_proc
        load_model_fn.assert_called_once()
        load_proc_fn.assert_called_once()
        model_store.set_model.assert_any_call(model_key, fake_model)
        model_store.set_model.assert_any_call(proc_key, fake_proc)

    # -- Lazy flag set after loading ------------------------------------- #

    def test_flag_set_after_load(self, surya_available, model_store,
                                  flag_attr, method,
                                  load_model_attr, load_proc_attr,
                                  model_key, proc_key,
                                  attr_model, attr_proc):
        engine = OCREngine()
        assert getattr(engine, flag_attr) is False
        method(engine)
        assert getattr(engine, flag_attr) is True


# --------------------------------------------------------------------------- #
#  Public API — detect_text
# --------------------------------------------------------------------------- #

class TestDetectText:
    """OCR text extraction."""

    def test_basic(self, surya_available, model_store):
        lines = [
            _make_text_line("Hello", 0.95, [0, 0, 50, 20]),
            _make_text_line("World", 0.88, [0, 25, 60, 45]),
        ]
        ocr_module.run_ocr.return_value = [_make_page_result(lines)]

        engine = OCREngine()
        result = engine.detect_text([MagicMock(), MagicMock()])

        assert len(result) == 1
        assert result[0]["lines"] == [
            {"text": "Hello", "confidence": 0.95, "bbox": [0, 0, 50, 20]},
            {"text": "World", "confidence": 0.88, "bbox": [0, 25, 60, 45]},
        ]
        assert result[0]["full_text"] == "Hello\nWorld"
        ocr_module.run_ocr.assert_called_once()

    def test_confidence_rounding(self, surya_available, model_store):
        line = _make_text_line("Precise", 0.95432, [0, 0, 10, 10])
        ocr_module.run_ocr.return_value = [_make_page_result([line])]

        engine = OCREngine()
        result = engine.detect_text([MagicMock()])

        assert result[0]["lines"][0]["confidence"] == 0.9543

    @pytest.mark.parametrize(
        "languages, expected_per_image",
        [
            (None, ["en"]),
            (["de"], ["de"]),
            (["en", "fr"], ["en", "fr"]),
        ],
    )
    def test_languages(self, surya_available, model_store,
                       languages, expected_per_image):
        images = [MagicMock(), MagicMock(), MagicMock()]
        ocr_module.run_ocr.return_value = [
            _make_page_result() for _ in images
        ]

        engine = OCREngine()
        engine.detect_text(images, languages=languages)

        _call_langs = ocr_module.run_ocr.call_args[0][1]
        expected = [expected_per_image] * len(images)
        assert _call_langs == expected

    def test_empty_images(self, surya_available, model_store):
        ocr_module.run_ocr.return_value = []

        engine = OCREngine()
        result = engine.detect_text([])

        assert result == []
        ocr_module.run_ocr.assert_called_once()


# --------------------------------------------------------------------------- #
#  Public API — detect_layout
# --------------------------------------------------------------------------- #

class TestDetectLayout:
    """Page layout region detection."""

    def test_basic(self, surya_available, model_store):
        regions = [
            _make_region("Text", [0, 0, 100, 50], 0.95),
            _make_region("Figure", [100, 0, 200, 100], 0.88),
            _make_region("Table", [0, 100, 150, 200], 0.91),
        ]
        ocr_module.batch_layout_detection.return_value = [
            _make_layout_page(regions),
        ]

        engine = OCREngine()
        result = engine.detect_layout([MagicMock()])

        assert len(result) == 1
        assert len(result[0]) == 3
        assert result[0][0] == {
            "label": "Text", "bbox": [0, 0, 100, 50], "confidence": 0.95,
        }
        assert result[0][1] == {
            "label": "Figure", "bbox": [100, 0, 200, 100], "confidence": 0.88,
        }
        assert result[0][2] == {
            "label": "Table", "bbox": [0, 100, 150, 200], "confidence": 0.91,
        }
        ocr_module.batch_text_detection.assert_called_once()
        ocr_module.batch_layout_detection.assert_called_once()

    def test_confidence_rounding(self, surya_available, model_store):
        region = _make_region("Text", [0, 0, 10, 10], 0.87654)
        ocr_module.batch_layout_detection.return_value = [
            _make_layout_page([region]),
        ]

        engine = OCREngine()
        result = engine.detect_layout([MagicMock()])
        assert result[0][0]["confidence"] == 0.8765

    def test_without_confidence(self, surya_available, model_store):
        region = MagicMock(spec=["label", "bbox"])
        region.label = "Header"
        region.bbox = [0, 0, 200, 30]

        ocr_module.batch_layout_detection.return_value = [
            _make_layout_page([region]),
        ]

        engine = OCREngine()
        result = engine.detect_layout([MagicMock()])

        assert result[0][0]["confidence"] is None

    def test_empty_images(self, surya_available, model_store):
        ocr_module.batch_layout_detection.return_value = []

        engine = OCREngine()
        result = engine.detect_layout([])

        assert result == []


# --------------------------------------------------------------------------- #
#  Public API — detect_reading_order
# --------------------------------------------------------------------------- #

class TestDetectReadingOrder:
    """Reading-order detection."""

    def test_basic(self, surya_available, model_store):
        items = [
            _make_order_item(0, [0, 0, 100, 50], "SectionHeader"),
            _make_order_item(1, [0, 60, 100, 100], "BodyText"),
            _make_order_item(2, [200, 0, 300, 200], "Figure"),
        ]
        ocr_module.batch_ordering.return_value = [_make_order_page(items)]

        engine = OCREngine()
        result = engine.detect_reading_order([MagicMock()])

        assert len(result) == 1
        assert len(result[0]) == 3
        assert result[0][0] == {
            "bbox": [0, 0, 100, 50],
            "position": 0,
            "label": "SectionHeader",
        }
        ocr_module.batch_text_detection.assert_called_once()
        ocr_module.batch_ordering.assert_called_once()

    def test_sorts_by_position(self, surya_available, model_store):
        items = [
            _make_order_item(3, [0, 100, 100, 50], "Footnote"),
            _make_order_item(1, [0, 50, 100, 50], "BodyText"),
            _make_order_item(0, [0, 0, 100, 50], "Header"),
            _make_order_item(2, [100, 0, 200, 100], "Figure"),
        ]
        ocr_module.batch_ordering.return_value = [_make_order_page(items)]

        engine = OCREngine()
        result = engine.detect_reading_order([MagicMock()])

        positions = [r["position"] for r in result[0]]
        assert positions == [0, 1, 2, 3]

    def test_items_without_label(self, surya_available, model_store):
        item = MagicMock(spec=["position", "bbox"])
        item.position = 0
        item.bbox = [0, 0, 100, 50]

        ocr_module.batch_ordering.return_value = [_make_order_page([item])]

        engine = OCREngine()
        result = engine.detect_reading_order([MagicMock()])

        assert result[0][0]["label"] == "text"

    def test_empty_images(self, surya_available, model_store):
        ocr_module.batch_ordering.return_value = []

        engine = OCREngine()
        result = engine.detect_reading_order([])

        assert result == []


# --------------------------------------------------------------------------- #
#  is_scanned_pdf
# --------------------------------------------------------------------------- #

class TestIsScannedPDF:
    """Heuristic for detecting scanned / image-based PDFs."""

    def make_engine(self):
        return OCREngine()

    @pytest.mark.parametrize(
        "text, page_count, expected",
        [
            # page_count <= 0 → False
            ("", 0, False),
            ("", -1, False),
            ("some text", 0, False),
            # chars_per_page >= 50 → False (not scanned)
            ("a" * 150, 3, False),
            ("a" * 50, 1, False),
            ("a" * 100, 2, False),
            # chars_per_page < 50 → True (scanned)
            ("", 1, True),
            ("a" * 49, 1, True),
            ("a" * 99, 2, True),
            ("   ", 1, True),
            ("a" * 149, 3, True),
            # whitespace stripped before counting
            ("  " + "a" * 49 + "  ", 1, True),
            ("  " + "a" * 50 + "  ", 1, False),
        ],
    )
    def test_is_scanned(self, surya_available, text, page_count, expected):
        engine = self.make_engine()
        assert engine.is_scanned_pdf(text, page_count) is expected


# --------------------------------------------------------------------------- #
#  Integration of lazy-loading paths inside public methods
# --------------------------------------------------------------------------- #

class TestLazyLoadingIntegration:
    """Verify that public methods correctly trigger lazy loading."""

    def test_detect_text_triggers_both_loads(self, surya_available, model_store):
        ocr_module.run_ocr.return_value = [_make_page_result()]
        engine = OCREngine()

        engine.detect_text([MagicMock()])

        assert engine._loaded_det is True
        assert engine._loaded_rec is True
        assert engine._loaded_order is False  # ordering not needed for OCR

    def test_detect_layout_triggers_detection(self, surya_available, model_store):
        ocr_module.batch_layout_detection.return_value = [_make_layout_page()]
        engine = OCREngine()

        engine.detect_layout([MagicMock()])

        assert engine._loaded_det is True
        assert engine._loaded_rec is False
        assert engine._loaded_order is False

    def test_detect_reading_order_triggers_detection_and_ordering(
        self, surya_available, model_store,
    ):
        ocr_module.batch_ordering.return_value = [_make_order_page()]
        engine = OCREngine()

        engine.detect_reading_order([MagicMock()])

        assert engine._loaded_det is True
        assert engine._loaded_rec is False
        assert engine._loaded_order is True

    def test_second_call_does_not_reload(self, surya_available, model_store):
        """Second call uses cached models – no extra load* calls."""
        ocr_module.run_ocr.return_value = [_make_page_result()]
        engine = OCREngine()

        engine.detect_text([MagicMock()])
        ocr_module.run_ocr.reset_mock()
        ocr_module.load_det_model.reset_mock()
        ocr_module.load_rec_model.reset_mock()

        engine.detect_text([MagicMock()])
        ocr_module.run_ocr.assert_called_once()
        ocr_module.load_det_model.assert_not_called()
        ocr_module.load_rec_model.assert_not_called()
