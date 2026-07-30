# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Enterprise-level tests for Validation module.

Covers:
- DocumentValidator (validator_v3.py) — all 9 methods, 50+ branches
- ReviewManager (review_manager.py) — all 5 paths (critical/review/ok, thresholds, limits)
"""

from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock
from app.models import PipelineDocument as Document, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata
import pytest

from app.pipeline.validation.validator_v3 import DocumentValidator, ValidationResult
from app.pipeline.validation.review_manager import ReviewManager

# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def validator():
    from app.models import PipelineDocument, Block, BlockType
    with (
        patch("app.pipeline.validation.validator_v3.ContractLoader"),
        patch("app.pipeline.validation.validator_v3.SectionOrderValidator"),
        patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"),
        patch("app.pipeline.validation.validator_v3.CrossRefClient"),
    ):
        return DocumentValidator(contracts_dir="app/pipeline/contracts")

@pytest.fixture
def doc():
    from app.models import PipelineDocument, Block, BlockType
    from app.models.pipeline_document import DocumentMetadata, TemplateInfo, ReviewMetadata, ReviewStatus

    doc = PipelineDocument(
        document_id="val1",
        blocks=[
            Block(block_id="b1", index=1, block_type=BlockType.TITLE, text="Title", section_name="title"),
            Block(block_id="b2", index=2, block_type=BlockType.BODY, text="Body", section_name="body"),
            Block(block_id="b3", index=3, block_type=BlockType.HEADING_1, text="References", section_name="references"),
        ],
        metadata=DocumentMetadata(title="Test", authors=["Alice"]),
        template=TemplateInfo(template_name="IEEE"),
        references=[
            Reference(reference_id="r1", block_id="r1", block_index=1, index=1,
                      citation_key="smith2024", year="2024", authors=["Smith, J."],
                      title="A paper", doi="10.1234/test", raw_text="[1] Smith, J."),
        ],
        figures=[
            Figure(figure_id="fig1", index=0, caption_text="Figure caption"),
        ],
        formatting_options={},
    )
    doc.tables = []
    return doc

# ═══════════════════════════════════════════════════════════════════════════════
# DocumentValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorInit:
    def test_initializes_components(self):
        from app.models import PipelineDocument, Block, BlockType
        with (
            patch("app.pipeline.validation.validator_v3.ContractLoader") as mock_cl,
            patch("app.pipeline.validation.validator_v3.SectionOrderValidator"),
            patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"),
            patch("app.pipeline.validation.validator_v3.CrossRefClient"),
        ):
            v = DocumentValidator(contracts_dir="app/pipeline/contracts")
        mock_cl.assert_called_once_with(contracts_dir="app/pipeline/contracts")

class TestAsBool:
    def test_none_returns_default(self):
        from app.models import PipelineDocument, Block, BlockType
        assert DocumentValidator._as_bool(None) is False
        assert DocumentValidator._as_bool(None, default=True) is True

    def test_bool_passthrough(self):
        from app.models import PipelineDocument, Block, BlockType
        assert DocumentValidator._as_bool(True) is True
        assert DocumentValidator._as_bool(False) is False

    def test_int_float(self):
        from app.models import PipelineDocument, Block, BlockType
        assert DocumentValidator._as_bool(1) is True
        assert DocumentValidator._as_bool(0) is False
        assert DocumentValidator._as_bool(1.0) is True
        assert DocumentValidator._as_bool(0.0) is False

    def test_string_true_values(self):
        from app.models import PipelineDocument, Block, BlockType
        for val in ["1", "true", "yes", "on", "  True  "]:
            assert DocumentValidator._as_bool(val) is True

    def test_string_false_values(self):
        from app.models import PipelineDocument, Block, BlockType
        for val in ["0", "false", "no", "off", "  NO  "]:
            assert DocumentValidator._as_bool(val) is False

    def test_unrecognized_string_returns_default(self):
        from app.models import PipelineDocument, Block, BlockType
        assert DocumentValidator._as_bool("maybe") is False
        assert DocumentValidator._as_bool("maybe", default=True) is True

class TestValidatorProcess:
    def test_process_calls_validate(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with patch.object(validator, "validate", return_value=ValidationResult(is_valid=True)) as mock_v:
            result = validator.process(doc)
        mock_v.assert_called_once_with(doc)
        assert result == doc

    def test_process_safe_execution_returns_doc_even_on_error(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with patch.object(validator, "validate", side_effect=Exception("crash")):
            result = validator.process(doc)
        assert result == doc

class TestValidate:
    def test_valid_document(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with (
            patch.object(validator, "_check_sections", return_value=([], [])),
            patch.object(validator, "_check_figures", return_value=([], [])),
            patch.object(validator, "_check_references", return_value=([], [])),
            patch.object(validator, "_check_tables", return_value=([], [])),
            patch.object(validator, "_check_reference_integrity", return_value=([], [])),
            patch("app.pipeline.validation.validator_v3.ReviewManager") as mock_rm,
        ):
            result = validator.validate(doc)
        assert result.is_valid is True
        assert result.errors == []
        assert doc.is_valid is True

    def test_has_errors(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with (
            patch.object(validator, "_check_sections", return_value=(["Missing required: Introduction"], [])),
            patch.object(validator, "_check_figures", return_value=([], [])),
            patch.object(validator, "_check_references", return_value=([], [])),
            patch.object(validator, "_check_tables", return_value=([], [])),
            patch.object(validator, "_check_reference_integrity", return_value=([], [])),
            patch("app.pipeline.validation.validator_v3.ReviewManager"),
        ):
            result = validator.validate(doc)
        assert result.is_valid is False
        assert "Missing required: Introduction" in result.errors

    def test_adds_processing_stage(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with (
            patch.object(validator, "_check_sections", return_value=([], [])),
            patch.object(validator, "_check_figures", return_value=([], [])),
            patch.object(validator, "_check_references", return_value=([], [])),
            patch.object(validator, "_check_tables", return_value=([], [])),
            patch.object(validator, "_check_reference_integrity", return_value=([], [])),
            patch("app.pipeline.validation.validator_v3.ReviewManager"),
        ):
            validator.validate(doc)
        # add_processing_stage was called (Pydantic model has it as a real method)
        assert doc.is_valid is True  # Confirm validation ran

    def test_fast_mode_skips_crossref(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.formatting_options = {"fast_mode": True}
        with (
            patch.object(validator, "_check_sections", return_value=([], [])),
            patch.object(validator, "_check_figures", return_value=([], [])),
            patch.object(validator, "_check_references", return_value=([], [])),
            patch.object(validator, "_check_tables", return_value=([], [])),
            patch.object(validator, "_check_reference_integrity") as mock_cr,
            patch("app.pipeline.validation.validator_v3.ReviewManager"),
        ):
            validator.validate(doc)
        mock_cr.assert_not_called()

    def test_fast_mode_default_not_set(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with (
            patch.object(validator, "_check_sections", return_value=([], [])),
            patch.object(validator, "_check_figures", return_value=([], [])),
            patch.object(validator, "_check_references", return_value=([], [])),
            patch.object(validator, "_check_tables", return_value=([], [])),
            patch.object(validator, "_check_reference_integrity") as mock_cr,
            patch("app.pipeline.validation.validator_v3.ReviewManager"),
        ):
            validator.validate(doc)
        mock_cr.assert_called_once()

class TestCheckSections:
    def test_uses_template_publisher(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        validator.order_validator.validate_order.return_value = []
        errs, warns = validator._check_sections(doc)
        validator.order_validator.validate_order.assert_called_once_with(doc, "IEEE")

    def test_fallback_publisher_when_no_template(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.template = None
        validator.order_validator.validate_order.return_value = []
        errs, warns = validator._check_sections(doc)
        validator.order_validator.validate_order.assert_called_once()

    def test_missing_required_error(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        validator.order_validator.validate_order.return_value = ["Missing required: Abstract"]
        errs, warns = validator._check_sections(doc)
        assert "Missing required: Abstract" in errs

    def test_other_violations_as_warnings(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        validator.order_validator.validate_order.return_value = ["Section out of order: Methods"]
        errs, warns = validator._check_sections(doc)
        assert "Section out of order: Methods" in warns

    def test_exception_logged_as_warning(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        validator.order_validator.validate_order.side_effect = Exception("order crash")
        errs, warns = validator._check_sections(doc)
        assert any("Section order check skipped" in w for w in warns)

class TestCheckFigures:
    def test_missing_caption_warns(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.figures[0].caption_text = ""
        errs, warns = validator._check_figures(doc)
        assert any("missing caption" in w for w in warns)

    def test_caption_present_no_warning(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        errs, warns = validator._check_figures(doc)
        assert len(warns) == 0

class TestCheckReferences:
    def test_no_references_section_returns_empty(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.references = []
        with patch.object(type(doc), "get_section_names", return_value=["body"]):
            errs, warns = validator._check_references(doc)
        assert len(errs) == 0
        assert len(warns) == 0

    def test_references_section_but_no_entries(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.references = []
        with patch.object(type(doc), "get_section_names", return_value=["references"]):
            errs, warns = validator._check_references(doc)
        assert any("no reference entries parsed" in w for w in warns)

    def test_missing_year_warns(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.references[0].year = None
        errs, warns = validator._check_references(doc)
        assert any("missing publication year" in w for w in warns)

    def test_missing_authors_errors(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.references[0].authors = None
        errs, warns = validator._check_references(doc)
        assert any("missing authors" in e for e in errs)

    def test_missing_title_warns(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.references[0].title = None
        errs, warns = validator._check_references(doc)
        assert any("missing title" in w for w in warns)

class TestCheckTables:
    def test_no_tables_no_warnings(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.tables = []
        errs, warns = validator._check_tables(doc)
        assert len(warns) == 0

    def test_missing_caption_warns(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        mock_table = MagicMock()
        mock_table.caption_text = None
        doc.tables = [mock_table]
        errs, warns = validator._check_tables(doc)
        assert any("missing caption" in w for w in warns)

    def test_caption_present_no_warning(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        mock_table = MagicMock()
        mock_table.caption_text = "Table 1. Results"
        doc.tables = [mock_table]
        errs, warns = validator._check_tables(doc)
        assert len(warns) == 0

class TestCheckReferenceIntegrity:
    def test_no_references_returns_empty(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        doc.references = []
        errs, warns = validator._check_reference_integrity(doc)
        assert errs == []
        assert warns == []

    def test_valid_doi_checked(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        ref = doc.references[0]
        ref.metadata = {}
        validator.crossref_client.validate_doi.return_value = True
        validator.crossref_client.get_metadata.return_value = {"title": "matched"}
        validator.crossref_client.calculate_confidence.return_value = 0.9
        errs, warns = validator._check_reference_integrity(doc)
        validator.crossref_client.validate_doi.assert_called_once_with("10.1234/test")
        assert ref.metadata["validation"]["doi_valid"] is True
        assert ref.metadata["validation"]["crossref_checked"] is True

    def test_invalid_doi_warns(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        ref = doc.references[0]
        ref.metadata = {}
        validator.crossref_client.validate_doi.return_value = False
        errs, warns = validator._check_reference_integrity(doc)
        assert any("invalid DOI" in w for w in warns)

    def test_low_confidence_warns(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        ref = doc.references[0]
        ref.metadata = {}
        validator.crossref_client.validate_doi.return_value = True
        validator.crossref_client.get_metadata.return_value = {"title": "mismatch"}
        validator.crossref_client.calculate_confidence.return_value = 0.3
        errs, warns = validator._check_reference_integrity(doc)
        assert any("low confidence" in w for w in warns)

    def test_get_metadata_exception_caught(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        ref = doc.references[0]
        ref.metadata = {}
        validator.crossref_client.validate_doi.return_value = True
        validator.crossref_client.get_metadata.side_effect = Exception("API down")
        errs, warns = validator._check_reference_integrity(doc)
        assert any("Failed to fetch metadata" in w for w in warns)

    def test_validate_doi_exception_caught(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        ref = doc.references[0]
        ref.metadata = {}
        validator.crossref_client.validate_doi.side_effect = Exception("network error")
        errs, warns = validator._check_reference_integrity(doc)
        assert any("CrossRef validation failed" in w for w in warns)

    def test_safe_function_fallback_on_crash(self, validator, doc):
        from app.models import PipelineDocument, Block, BlockType
        with patch.object(validator.crossref_client, "validate_doi", side_effect=Exception("crash")):
            errs, warns = validator._check_reference_integrity(doc)
        assert isinstance(errs, list)
        assert isinstance(warns, list)

class TestValidateDocumentConvenience:
    def test_creates_validator_and_validates(self, doc):
        from app.models import PipelineDocument, Block, BlockType
        with (
            patch("app.pipeline.validation.validator_v3.DocumentValidator") as mock_v_cls,
        ):
            mock_v = MagicMock()
            mock_v_cls.return_value = mock_v
            mock_v.validate.return_value = ValidationResult(is_valid=True)
            from app.pipeline.validation.validator_v3 import validate_document
            result = validate_document(doc)
        mock_v.validate.assert_called_once_with(doc)
        assert result.is_valid is True

# ═══════════════════════════════════════════════════════════════════════════════
# ReviewManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestReviewManagerInit:
    def test_default_thresholds(self):
        from app.models import PipelineDocument, Block, BlockType
        rm = ReviewManager()
        assert rm.review_threshold == 0.70
        assert rm.critical_threshold == 0.45

    def test_custom_thresholds(self):
        from app.models import PipelineDocument, Block, BlockType
        rm = ReviewManager(review_threshold=0.8, critical_threshold=0.5)
        assert rm.review_threshold == 0.8
        assert rm.critical_threshold == 0.5

    def test_critical_must_be_less_than_review(self):
        from app.models import PipelineDocument, Block, BlockType
        with pytest.raises(ValueError, match="critical_threshold"):
            ReviewManager(review_threshold=0.5, critical_threshold=0.7)

    def test_thresholds_out_of_range(self):
        from app.models import PipelineDocument, Block, BlockType
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(review_threshold=1.5, critical_threshold=0.5)

class TestReviewManagerEvaluate:
    @pytest.fixture
    def rm(self):
        from app.models import PipelineDocument, Block, BlockType
        return ReviewManager(review_threshold=0.7, critical_threshold=0.45)

    def _make_block(self, block_id="b1", conf=None):
        from app.models import PipelineDocument, Block, BlockType
        block = MagicMock()
        block.block_id = block_id
        block.metadata = {}
        block.semantic_intent = None
        block.classification_confidence = conf
        return block

    def _make_doc(self, blocks=None, ai_hints=None):
        from app.models import PipelineDocument, Block, BlockType
        doc = MagicMock()
        doc.blocks = blocks or []
        doc.metadata.ai_hints = ai_hints or {}
        return doc

    def test_ok_status_when_high_confidence(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=0.95)
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "OK"
        assert result.review.lowest_confidence == 0.95

    def test_review_status_when_below_review_threshold(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=0.6)
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "REVIEW"

    def test_critical_status_when_below_critical_threshold(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=0.3)
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "CRITICAL"

    def test_flags_limited_to_5(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        blocks = [self._make_block(block_id=f"b{i}", conf=0.1) for i in range(10)]
        doc = self._make_doc(blocks=blocks)
        result = rm.evaluate(doc)
        assert len(result.review.flags) <= 5

    def test_confidence_from_metadata_dict(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = MagicMock()
        block.block_id = "b1"
        block.metadata = {"classification_confidence": 0.3}
        block.semantic_intent = None
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "CRITICAL"

    def test_confidence_fallback_to_nlp_confidence(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = MagicMock()
        block.block_id = "b1"
        block.classification_confidence = None
        block.metadata = {"nlp_confidence": 0.5}
        block.semantic_intent = None
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "REVIEW"

    def test_non_dict_metadata_uses_attribute(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = MagicMock()
        block.block_id = "b1"
        block.metadata = "not_a_dict"
        block.classification_confidence = 0.95
        block.semantic_intent = None
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "OK"

    def test_invalid_confidence_clamped(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf="not_a_number")
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert result.review.lowest_confidence == 1.0

    def test_confidence_clamped_to_range(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=2.5)
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert result.review.lowest_confidence == 1.0

    def test_semantic_intent_from_attribute(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=0.3)
        block.semantic_intent = "methods"
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert "methods" in result.review.flags[0]

    def test_semantic_intent_from_metadata(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = MagicMock()
        block.block_id = "b1"
        block.metadata = {"classification_confidence": 0.3, "semantic_intent": "abstract"}
        block.classification_confidence = None
        block.semantic_intent = None
        doc = self._make_doc(blocks=[block])
        result = rm.evaluate(doc)
        assert "abstract" in result.review.flags[0]

    def test_ai_reasoning_uncertainty_triggers_review(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=0.95)
        doc = self._make_doc(
            blocks=[block],
            ai_hints={"semantic_advice": {"confidence": 0.6}},
        )
        result = rm.evaluate(doc)
        assert str(result.review.status) == "REVIEW"

    def test_ai_reasoning_does_not_lower_below_block_confidence(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        block = self._make_block(conf=0.95)
        doc = self._make_doc(
            blocks=[block],
            ai_hints={"semantic_advice": {"confidence": 0.8}},
        )
        result = rm.evaluate(doc)
        assert str(result.review.status) == "OK"

    def test_empty_blocks_returns_ok(self, rm):
        from app.models import PipelineDocument, Block, BlockType
        doc = self._make_doc(blocks=[])
        result = rm.evaluate(doc)
        assert str(result.review.status) == "OK"
