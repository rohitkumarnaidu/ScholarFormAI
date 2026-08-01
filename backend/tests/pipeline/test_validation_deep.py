# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


class TestValidationResult:
    def test_validation_result_defaults(self):
        from app.pipeline.validation.validator_v3 import ValidationResult
        r = ValidationResult(is_valid=True)
        assert r.is_valid is True
        assert r.errors == []
        assert r.warnings == []
        assert r.stats == {}
        assert r.timestamp is not None


class TestDocumentValidator:
    def test_init(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator(contracts_dir="/tmp/contracts")
                        assert v.contract_loader is not None
                        assert v.order_validator is not None
                        assert v.integrity_engine is not None
                        assert v.crossref_client is not None

    def test_as_bool_none(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(None) is False
        assert DocumentValidator._as_bool(None, True) is True

    def test_as_bool_bool(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(True) is True
        assert DocumentValidator._as_bool(False) is False

    def test_as_bool_number(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(1) is True
        assert DocumentValidator._as_bool(0) is False
        assert DocumentValidator._as_bool(0.0) is False
        assert DocumentValidator._as_bool(3.14) is True

    def test_as_bool_string_true(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool("true") is True
        assert DocumentValidator._as_bool("1") is True
        assert DocumentValidator._as_bool("yes") is True
        assert DocumentValidator._as_bool("on") is True

    def test_as_bool_string_false(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool("false") is False
        assert DocumentValidator._as_bool("0") is False
        assert DocumentValidator._as_bool("no") is False
        assert DocumentValidator._as_bool("off") is False

    def test_as_bool_unknown_string(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool("maybe") is False
        assert DocumentValidator._as_bool("maybe", True) is True

    def test_process(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        with patch.object(DocumentValidator, "validate"):
            with patch("app.pipeline.validation.validator_v3.ContractLoader"):
                with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                    with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                        with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                            v = DocumentValidator()
                            result = v.process(doc)
                            assert result is doc

    def test_validate_success(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.figures = []
        doc.references = []
        doc.tables = []
        doc.formatting_options = {}
        doc.get_stats.return_value = {}
        doc.get_section_names.return_value = ["introduction"]
        doc.metadata.ai_hints = {}

        with patch.object(DocumentValidator, "_check_sections", return_value=([], [])):
            with patch.object(DocumentValidator, "_check_figures", return_value=([], [])):
                with patch.object(DocumentValidator, "_check_references", return_value=([], [])):
                    with patch.object(DocumentValidator, "_check_tables", return_value=([], [])):
                        with patch.object(DocumentValidator, "_check_reference_integrity", return_value=([], [])):
                            with patch("app.pipeline.validation.validator_v3.ContractLoader"):
                                with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                                    with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                                        with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                                            v = DocumentValidator()
                                            v.integrity_engine.validate_integrity.return_value = []
                                            result = v.validate(doc)
                                            assert result.is_valid is True

    def test_validate_with_errors(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.figures = []
        doc.references = []
        doc.tables = []
        doc.formatting_options = {}
        doc.get_stats.return_value = {}
        doc.get_section_names.return_value = []
        doc.metadata.ai_hints = {}

        with patch.object(DocumentValidator, "_check_sections", return_value=(["Missing required: methods"], [])):
            with patch.object(DocumentValidator, "_check_figures", return_value=([], [])):
                with patch.object(DocumentValidator, "_check_references", return_value=([], [])):
                    with patch.object(DocumentValidator, "_check_tables", return_value=([], [])):
                        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
                            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                                        v = DocumentValidator()
                                        v.integrity_engine.validate_integrity.return_value = []
                                        result = v.validate(doc)
                                        assert result.is_valid is False
                                        assert len(result.errors) > 0

    def test_validate_integrity_dangling(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.figures = []
        doc.references = []
        doc.tables = []
        doc.formatting_options = {}
        doc.get_stats.return_value = {}
        doc.get_section_names.return_value = []
        doc.metadata.ai_hints = {}

        with patch.object(DocumentValidator, "_check_sections", return_value=([], [])):
            with patch.object(DocumentValidator, "_check_figures", return_value=([], [])):
                with patch.object(DocumentValidator, "_check_references", return_value=([], [])):
                    with patch.object(DocumentValidator, "_check_tables", return_value=([], [])):
                        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
                            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                                        v = DocumentValidator()
                                        v.integrity_engine.validate_integrity.return_value = ["Dangling reference to fig_1"]
                                        result = v.validate(doc)
                                        assert "Dangling" in str(result.errors)

    def test_validate_fast_mode_skips_doi(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.figures = []
        doc.references = [MagicMock()]
        doc.tables = []
        doc.formatting_options = {"fast_mode": True}
        doc.get_stats.return_value = {}
        doc.get_section_names.return_value = []
        doc.metadata.ai_hints = {}

        with patch.object(DocumentValidator, "_check_sections", return_value=([], [])):
            with patch.object(DocumentValidator, "_check_figures", return_value=([], [])):
                with patch.object(DocumentValidator, "_check_references", return_value=([], [])):
                    with patch.object(DocumentValidator, "_check_tables", return_value=([], [])):
                        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
                            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                                        v = DocumentValidator()
                                        v.integrity_engine.validate_integrity.return_value = []
                                        with patch.object(v, "_check_reference_integrity") as mock_doi:
                                            v.validate(doc)
                                            mock_doi.assert_not_called()

    def test_check_sections_error(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.template.template_name = "IEEE"
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.order_validator.validate_order.return_value = ["Missing required: abstract"]
                        errors, warnings = v._check_sections(doc)
                        assert len(errors) == 1
                        assert "Missing required" in errors[0]

    def test_check_sections_warning(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.template.template_name = "IEEE"
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.order_validator.validate_order.return_value = ["Out of order: methods before introduction"]
                        errors, warnings = v._check_sections(doc)
                        assert len(errors) == 0
                        assert len(warnings) == 1

    def test_check_sections_no_template(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.template = None
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.order_validator.validate_order.return_value = []
                        errors, warnings = v._check_sections(doc)
                        assert errors == []

    def test_check_sections_order_exception(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.template.template_name = "IEEE"
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.order_validator.validate_order.side_effect = Exception("Order error")
                        errors, warnings = v._check_sections(doc)
                        assert errors == []
                        assert len(warnings) == 1

    def test_check_figures_missing_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        fig = MagicMock()
        fig.has_caption.return_value = False
        fig.figure_id = "fig_1"
        doc.figures = [fig]
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        errors, warnings = v._check_figures(doc)
                        assert len(warnings) == 1
                        assert "missing caption" in warnings[0]

    def test_check_references_empty_with_section(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.references = []
        doc.get_section_names.return_value = ["references"]
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        errors, warnings = v._check_references(doc)
                        assert len(warnings) == 1

    def test_check_references_empty_no_section(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.references = []
        doc.get_section_names.return_value = []
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        errors, warnings = v._check_references(doc)
                        assert len(warnings) == 0

    def test_check_references_missing_fields(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        ref = MagicMock()
        ref.year = None
        ref.authors = []
        ref.title = None
        ref.citation_key = "ref1"
        doc.references = [ref]
        doc.get_section_names.return_value = []
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        errors, warnings = v._check_references(doc)
                        assert len(errors) == 1
                        assert len(warnings) == 2

    def test_check_tables_missing_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        table = MagicMock()
        table.caption_text = None
        doc.tables = [table]
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        errors, warnings = v._check_tables(doc)
                        assert len(warnings) == 1

    def test_check_reference_integrity_no_refs(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        doc.references = []
        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        errors, warnings = v._check_reference_integrity(doc)
                        assert errors == []
                        assert warnings == []

    def test_check_reference_integrity_with_doi(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        ref = MagicMock()
        ref.has_doi.return_value = True
        ref.doi = "10.1234/test"
        ref.citation_key = "ref1"
        ref.metadata = {}
        doc.references = [ref]

        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.crossref_client.validate_doi.return_value = True
                        v.crossref_client.get_metadata.return_value = {"title": "Test"}
                        v.crossref_client.calculate_confidence.return_value = 0.8
                        errors, warnings = v._check_reference_integrity(doc)
                        assert errors == []
                        assert ref.metadata["validation"]["doi_valid"] is True

    def test_check_reference_integrity_invalid_doi(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        ref = MagicMock()
        ref.has_doi.return_value = True
        ref.doi = "10.1234/bad"
        ref.citation_key = "ref1"
        ref.metadata = {}
        doc.references = [ref]

        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.crossref_client.validate_doi.return_value = False
                        errors, warnings = v._check_reference_integrity(doc)
                        assert "invalid DOI" in warnings[0]

    def test_check_reference_integrity_low_confidence(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        ref = MagicMock()
        ref.has_doi.return_value = True
        ref.doi = "10.1234/low"
        ref.citation_key = "ref1"
        ref.metadata = {}
        doc.references = [ref]

        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.crossref_client.validate_doi.return_value = True
                        v.crossref_client.get_metadata.return_value = {"title": "Test"}
                        v.crossref_client.calculate_confidence.return_value = 0.3
                        errors, warnings = v._check_reference_integrity(doc)
                        assert "low confidence" in warnings[0]

    def test_check_reference_integrity_validation_exception(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        doc = MagicMock()
        ref = MagicMock()
        ref.has_doi.return_value = True
        ref.doi = "10.1234/test"
        ref.citation_key = "ref1"
        ref.metadata = {}
        doc.references = [ref]

        with patch("app.pipeline.validation.validator_v3.ContractLoader"):
            with patch("app.pipeline.validation.validator_v3.SectionOrderValidator"):
                with patch("app.pipeline.validation.validator_v3.CrossReferenceEngine"):
                    with patch("app.pipeline.validation.validator_v3.CrossRefClient"):
                        v = DocumentValidator()
                        v.crossref_client.validate_doi.side_effect = Exception("API error")
                        errors, warnings = v._check_reference_integrity(doc)
                        assert "API error" in warnings[0]

    def test_validate_document_convenience(self):
        from app.pipeline.validation.validator_v3 import validate_document
        doc = MagicMock()
        doc.figures = []
        doc.references = []
        doc.tables = []
        doc.formatting_options = {}
        doc.get_stats.return_value = {}
        doc.get_section_names.return_value = []
        doc.metadata.ai_hints = {}
        doc.template = None

        with patch("app.pipeline.validation.validator_v3.DocumentValidator.validate") as mock_validate:
            mock_validate.return_value = MagicMock(is_valid=True)
            result = validate_document(doc)
            assert result.is_valid is True

    def test_validate_document_crash_fallback(self):
        from app.pipeline.validation.validator_v3 import ValidationResult, validate_document
        doc = MagicMock()
        doc.figures = []
        doc.references = []
        doc.tables = []
        doc.formatting_options = {}
        doc.get_stats.return_value = {}
        doc.get_section_names.return_value = []
        doc.metadata.ai_hints = {}

        with patch("app.pipeline.validation.validator_v3.DocumentValidator") as mock_cls:
            mock_cls.side_effect = Exception("Init failed")
            result = validate_document(doc)
            assert isinstance(result, ValidationResult)
            assert result.is_valid is False


class TestReviewManager:
    def test_init_defaults(self):
        from app.pipeline.validation.review_manager import ReviewManager
        rm = ReviewManager()
        assert rm.review_threshold == 0.70
        assert rm.critical_threshold == 0.45

    def test_init_invalid_thresholds(self):
        from app.pipeline.validation.review_manager import ReviewManager
        with pytest.raises(ValueError, match="critical_threshold"):
            ReviewManager(review_threshold=0.3, critical_threshold=0.5)
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(critical_threshold=-0.1)
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(critical_threshold=0.5, review_threshold=1.5)

    def test_evaluate_ok(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        doc = PipelineDocument(
            document_id="test",
            blocks=[Block(block_id="b1", text="OK", index=0, block_type=BlockType.BODY, classification_confidence=0.95)]
        )
        rm = ReviewManager()
        result = rm.evaluate(doc)
        from app.models.review import ReviewStatus
        assert result.review.status == ReviewStatus.OK

    def test_evaluate_review_threshold(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        doc = PipelineDocument(
            document_id="test",
            blocks=[Block(block_id="b1", text="Ambiguous", index=0, block_type=BlockType.BODY, classification_confidence=0.6)]
        )
        rm = ReviewManager()
        result = rm.evaluate(doc)
        from app.models.review import ReviewStatus
        assert result.review.status == ReviewStatus.REVIEW

    def test_evaluate_critical(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        doc = PipelineDocument(
            document_id="test",
            blocks=[Block(block_id="b1", text="Bad", index=0, block_type=BlockType.BODY, classification_confidence=0.3)]
        )
        rm = ReviewManager()
        result = rm.evaluate(doc)
        from app.models.review import ReviewStatus
        assert result.review.status == ReviewStatus.CRITICAL

    def test_evaluate_confidence_from_metadata(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        block = Block(block_id="b1", text="Test", index=0, block_type=BlockType.BODY)
        block.metadata["classification_confidence"] = 0.3
        doc = PipelineDocument(document_id="test", blocks=[block])
        rm = ReviewManager()
        result = rm.evaluate(doc)
        from app.models.review import ReviewStatus
        assert result.review.status == ReviewStatus.CRITICAL

    def test_evaluate_confidence_from_nlp_metadata(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        block = Block(block_id="b1", text="Test", index=0, block_type=BlockType.BODY)
        block.metadata["nlp_confidence"] = 0.5
        doc = PipelineDocument(document_id="test", blocks=[block])
        rm = ReviewManager()
        result = rm.evaluate(doc)
        from app.models.review import ReviewStatus
        assert result.review.status == ReviewStatus.REVIEW

    def test_evaluate_invalid_confidence(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        block = Block.model_construct(block_id="b1", text="Test", index=0, block_type=BlockType.BODY, classification_confidence="invalid")
        doc = PipelineDocument(document_id="test", blocks=[block])
        rm = ReviewManager()
        result = rm.evaluate(doc)
        assert result.review.lowest_confidence == 1.0

    def test_evaluate_ai_hints(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        doc = PipelineDocument(
            document_id="test",
            blocks=[Block(block_id="b1", text="Test", index=0, block_type=BlockType.BODY, classification_confidence=0.9)]
        )
        doc.metadata.ai_hints["semantic_advice"] = {"confidence": 0.5}
        rm = ReviewManager()
        result = rm.evaluate(doc)
        from app.models.review import ReviewStatus
        assert result.review.status == ReviewStatus.REVIEW

    def test_evaluate_flags_limited_to_five(self):
        from app.models.block import Block, BlockType
        from app.models.pipeline_document import PipelineDocument
        from app.pipeline.validation.review_manager import ReviewManager
        blocks = [Block(block_id=f"b{i}", text="Low", index=i, block_type=BlockType.BODY, classification_confidence=0.3) for i in range(10)]
        doc = PipelineDocument(document_id="test", blocks=blocks)
        rm = ReviewManager()
        result = rm.evaluate(doc)
        assert len(result.review.flags) <= 5
