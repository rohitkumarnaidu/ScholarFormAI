from datetime import date, datetime, time
from enum import Enum
from unittest.mock import MagicMock


class TestSanitizeForJson:
    def test_string(self):
        from app.utils.serialization import sanitize_for_json
        assert sanitize_for_json("hello") == "hello"

    def test_int(self):
        from app.utils.serialization import sanitize_for_json
        assert sanitize_for_json(42) == 42

    def test_dict(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json({"a": 1, "b": [2, 3]})
        assert result == {"a": 1, "b": [2, 3]}

    def test_datetime(self):
        from app.utils.serialization import sanitize_for_json
        dt = datetime(2024, 6, 15, 10, 30, 0)
        result = sanitize_for_json(dt)
        assert "2024" in result

    def test_date(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json(date(2024, 6, 15))
        assert result == "2024-06-15"

    def test_enum(self):
        from app.utils.serialization import sanitize_for_json
        class Color(Enum):
            RED = "red"
        assert sanitize_for_json(Color.RED) == "red"

    def test_bytes(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json(b"hello")
        assert result["encoding"] == "binary"
        assert result["size_bytes"] == 5

    def test_tuple(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json((1, "a"))
        assert result == [1, "a"]

    def test_set(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json({3, 1, 2})
        assert result == [1, 2, 3]

    def test_none(self):
        from app.utils.serialization import sanitize_for_json
        assert sanitize_for_json(None) is None

    def test_time(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json(time(14, 30, 0))
        assert "14:30:00" in result

    def test_empty_bytes(self):
        from app.utils.serialization import sanitize_for_json
        result = sanitize_for_json(b"")
        assert result["preview_b64"] == ""


class TestSafeModelDump:
    def test_none(self):
        from app.utils.serialization import safe_model_dump
        assert safe_model_dump(None) == {}

    def test_pydantic_v2_model(self):
        from pydantic import BaseModel

        from app.utils.serialization import safe_model_dump
        class TestModel(BaseModel):
            name: str
        model = TestModel(name="test")
        result = safe_model_dump(model)
        assert result["name"] == "test"

    def test_dict_fallback(self):
        from app.utils.serialization import safe_model_dump
        result = safe_model_dump({"key": "value"})
        assert result == {"key": "value"}

    def test_non_dict_non_model(self):
        from app.utils.serialization import safe_model_dump
        result = safe_model_dump("just a string")
        assert result == {"value": "just a string"}

    def test_pydantic_v1_style_dict(self):
        from app.utils.serialization import safe_model_dump
        obj = MagicMock(spec=["dict"])
        obj.dict.return_value = {"name": "v1", "count": 3}
        result = safe_model_dump(obj)
        assert result == {"name": "v1", "count": 3}
        obj.dict.assert_called_once()

    def test_model_dump_mode_python_fallback(self):
        from app.utils.serialization import safe_model_dump
        obj = MagicMock(spec=["model_dump"])
        calls = []
        def model_dump_side(mode="python"):
            calls.append(mode)
            if len(calls) == 1:
                raise ValueError("json mode fail")
            return {"data": "python", "nested": {"sub": [1, 2]}}
        obj.model_dump.side_effect = model_dump_side
        result = safe_model_dump(obj)
        assert result == {"data": "python", "nested": {"sub": [1, 2]}}
        assert len(calls) == 2

    def test_top_level_exception_returns_sanitized(self):
        from app.utils.serialization import safe_model_dump
        class ExplodingModel:
            @property
            def model_dump(self):
                raise RuntimeError("boom")
        result = safe_model_dump(ExplodingModel())
        assert isinstance(result, dict)


class TestNormalizeBlockType:
    def test_enum_with_value(self):
        from enum import Enum

        from app.utils.serialization import _normalize_block_type
        class BType(Enum):
            BODY = "body"
        assert _normalize_block_type(BType.BODY) == "body"

    def test_string(self):
        from app.utils.serialization import _normalize_block_type
        assert _normalize_block_type("body") == "body"

    def test_object_without_value(self):
        from app.utils.serialization import _normalize_block_type
        assert _normalize_block_type(42) == "42"


class TestBuildStructuredData:
    def test_basic_build(self):
        from app.utils.serialization import build_structured_data
        doc = MagicMock()
        doc.blocks = []
        doc.metadata = {"title": "Test"}
        doc.references = []
        doc.processing_history = []
        result = build_structured_data(doc)
        assert "sections" in result
        assert "blocks" in result
        assert "headings" in result
        assert result["metadata"]["title"] == "Test"

    def test_with_blocks(self):
        from app.utils.serialization import build_structured_data
        block = MagicMock()
        block.block_type = type("BT", (), {"value": "body"})()
        block.text = "Hello world"
        block.level = None
        block.section_name = None
        block.metadata = None
        doc = MagicMock()
        doc.blocks = [block]
        doc.metadata = None
        doc.references = []
        doc.processing_history = []
        result = build_structured_data(doc)
        assert len(result["blocks"]) == 1
        assert len(result["sections"]["body"]) == 1

    def test_heading_block(self):
        from app.utils.serialization import build_structured_data
        block = MagicMock()
        block.block_type = type("BT", (), {"value": "heading_1"})()
        block.text = "Introduction"
        block.level = 1
        block.section_name = "intro"
        block.metadata = None
        doc = MagicMock()
        doc.blocks = [block]
        doc.metadata = None
        doc.references = []
        doc.processing_history = []
        result = build_structured_data(doc)
        assert len(result["headings"]) == 1
        assert result["headings"][0]["text"] == "Introduction"
        assert result["headings"][0]["level"] == 1

    def test_heading_level_from_metadata(self):
        from app.utils.serialization import build_structured_data
        block = MagicMock()
        block.block_type = type("BT", (), {"value": "heading_2"})()
        block.text = "Methods"
        block.level = None
        block.section_name = None
        block.metadata = {"heading_level": 2}
        doc = MagicMock()
        doc.blocks = [block]
        doc.metadata = None
        doc.references = []
        doc.processing_history = []
        result = build_structured_data(doc)
        assert result["headings"][0]["level"] == 2

    def test_partial_flag(self):
        from app.utils.serialization import build_structured_data
        doc = MagicMock()
        doc.blocks = []
        doc.metadata = None
        doc.references = []
        doc.processing_history = []
        result = build_structured_data(doc, partial=True)
        assert result["partial"] is True

    def test_with_references_and_history(self):
        from app.utils.serialization import build_structured_data
        ref = MagicMock()
        ref.reference_id = "ref_001"
        stage = MagicMock()
        stage.stage_name = "parsing"
        doc = MagicMock()
        doc.blocks = []
        doc.metadata = None
        doc.references = [ref]
        doc.processing_history = [stage]
        result = build_structured_data(doc)
        assert len(result["references"]) == 1
        assert len(result["history"]) == 1

    def test_empty_blocks_no_error(self):
        from app.utils.serialization import build_structured_data
        doc = MagicMock()
        doc.blocks = None
        doc.metadata = None
        doc.references = []
        doc.processing_history = []
        result = build_structured_data(doc)
        assert result["blocks"] == []
        assert result["headings"] == []
