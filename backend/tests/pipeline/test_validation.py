# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from app.pipeline.validation.validator_v3 import (
    DocumentValidator, ValidationResult, validate_document
)
from app.pipeline.validation.review_manager import ReviewManager
from app.pipeline.validation.ai_explainer import AIExplainer
from app.models import PipelineDocument as Document, Block, BlockType, ReviewStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc(**overrides) -> Document:
    """Minimal PipelineDocument."""
    return Document(document_id="test-123", **overrides)


def _block(block_id: str = "b1", **kw) -> Block:
    return Block(block_id=block_id, index=0, text="Hello", **kw)


# ===========================================================================
# DocumentValidator
# ===========================================================================

class TestDocumentValidatorInit:
    def test_init_creates_dependencies(self):
        v = DocumentValidator()
        assert v.contract_loader is not None
        assert v.order_validator is not None
        assert v.integrity_engine is not None
        assert v.crossref_client is not None


class TestAsBool:
    def test_none_default(self):
        assert DocumentValidator._as_bool(None) is False
        assert DocumentValidator._as_bool(None, True) is True

    def test_bool_passthrough(self):
        assert DocumentValidator._as_bool(True) is True
        assert DocumentValidator._as_bool(False) is False

    def test_int_float(self):
        assert DocumentValidator._as_bool(1) is True
        assert DocumentValidator._as_bool(0) is False
        assert DocumentValidator._as_bool(1.0) is True
        assert DocumentValidator._as_bool(0.0) is False

    def test_string_values(self):
        assert DocumentValidator._as_bool("true") is True
        assert DocumentValidator._as_bool("yes") is True
        assert DocumentValidator._as_bool("1") is True
        assert DocumentValidator._as_bool("on") is True
        assert DocumentValidator._as_bool("false") is False
        assert DocumentValidator._as_bool("no") is False
        assert DocumentValidator._as_bool("0") is False
        assert DocumentValidator._as_bool("off") is False
        assert DocumentValidator._as_bool("maybe") is False


class TestDocumentValidatorProcess:
    def test_process_calls_validate(self):
        doc = _doc()
        v = DocumentValidator()
        v.validate = MagicMock(return_value=ValidationResult(is_valid=True))
        result = v.process(doc)
        v.validate.assert_called_once_with(doc)
        assert result is doc

    def test_process_safe_execution_fallback(self):
        doc = _doc()
        v = DocumentValidator()
        v.validate = MagicMock(side_effect=RuntimeError("boom"))
        result = v.process(doc)
        assert result is doc


class TestDocumentValidatorValidate:
    def test_validate_empty_document(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.multiple(v, _check_sections=MagicMock(return_value=([], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=([], []))):
            v.review_manager = MagicMock()
            result = v.validate(doc)
        assert result.is_valid is True
        assert doc.is_valid is True

    def test_validate_with_errors(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.multiple(v, _check_sections=MagicMock(return_value=(["Section missing"], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=([], []))):
            v.review_manager = MagicMock()
            result = v.validate(doc)
        assert result.is_valid is False
        assert doc.is_valid is False
        assert "Section missing" in doc.validation_errors

    def test_validate_integrity_violations(self):
        doc = _doc()
        v = DocumentValidator()
        v.integrity_engine.validate_integrity = MagicMock(return_value=[
            "Dangling reference to Fig. 1",
            "Warning: figure out of order"
        ])
        with patch.multiple(v, _check_sections=MagicMock(return_value=([], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=([], []))):
            v.review_manager = MagicMock()
            result = v.validate(doc)
        assert "Dangling reference to Fig. 1" in result.errors
        assert "Warning: figure out of order" in result.warnings

    def test_validate_fast_mode_skips_doi_checks(self):
        doc = _doc(formatting_options={"fast_mode": True})
        v = DocumentValidator()
        with patch.multiple(v, _check_sections=MagicMock(return_value=([], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=([], []))):
            v.review_manager = MagicMock()
            result = v.validate(doc)
        assert result.is_valid is True

    def test_validate_doi_warnings_non_fast(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.multiple(v, _check_sections=MagicMock(return_value=([], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=(["DOI error"], []))):
            v.review_manager = MagicMock()
            result = v.validate(doc)
        assert "DOI error" in result.warnings

    def test_validate_adds_processing_stage(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.multiple(v, _check_sections=MagicMock(return_value=([], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=([], []))):
            v.review_manager = MagicMock()
            v.validate(doc)
        assert len(doc.processing_history) >= 1
        stage = doc.processing_history[-1]
        assert stage.stage_name == "validation"
        assert stage.status in ("success", "warning")

    def test_validate_returns_stats(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.multiple(v, _check_sections=MagicMock(return_value=([], [])),
                            _check_figures=MagicMock(return_value=([], [])),
                            _check_references=MagicMock(return_value=([], [])),
                            _check_tables=MagicMock(return_value=([], [])),
                            _check_reference_integrity=MagicMock(return_value=([], []))):
            v.review_manager = MagicMock()
            result = v.validate(doc)
        assert "blocks" in result.stats
        assert "figures" in result.stats


class TestCheckSections:
    def test_delegates_to_order_validator(self):
        doc = _doc(blocks=[_block(section_name="Introduction")])
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=["Missing required: Abstract"])
        errors, warnings = v._check_sections(doc)
        assert "Missing required: Abstract" in errors
        assert len(warnings) == 0

    def test_non_missing_are_warnings(self):
        doc = _doc()
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=["Unusual order: Methods before Introduction"])
        errors, warnings = v._check_sections(doc)
        assert len(errors) == 0
        assert any("Unusual order" in w for w in warnings)

    def test_handles_exception_gracefully(self):
        doc = _doc()
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(side_effect=ValueError("boom"))
        errors, warnings = v._check_sections(doc)
        assert len(errors) == 0
        assert any("Section order check skipped" in w for w in warnings)

    def test_fallback_publisher(self):
        doc = _doc()
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "IEEE")

    def test_publisher_from_template(self):
        from app.models import TemplateInfo
        doc = _doc(blocks=[_block(section_name="Intro")],
                   template=TemplateInfo(template_name="ACM"))
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "ACM")

    def test_no_template_fallback(self):
        doc = _doc()
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "IEEE")


class TestCheckFigures:
    def test_figure_with_caption_no_warning(self):
        from app.models import Figure
        fig = Figure(figure_id="f1", index=0, caption_text="Fig. 1. Results")
        doc = _doc(figures=[fig])
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert errors == []
        assert warnings == []

    def test_figure_without_caption_warning(self):
        from app.models import Figure
        fig = Figure(figure_id="F1", index=0, caption_text=None)
        doc = _doc(figures=[fig])
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert "Figure F1 missing caption" in warnings

    def test_no_figures(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert errors == []
        assert warnings == []


class TestCheckReferences:
    def test_no_references_no_section_warns_nothing(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_references(doc)
        assert errors == []
        assert warnings == []

    def test_no_references_but_section_exists_warns(self):
        doc = _doc(blocks=[_block(section_name="References")])
        v = DocumentValidator()
        errors, warnings = v._check_references(doc)
        assert "References section found but no reference entries parsed" in warnings

    def test_ref_missing_year(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=None, authors=["Smith"], title="Paper")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        errors, warnings = v._check_references(doc)
        assert any("R1" in w and "year" in w for w in warnings)

    def test_ref_missing_authors_error(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=2023, authors=[], title="Paper")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        errors, warnings = v._check_references(doc)
        assert any("R1" in e and "authors" in e for e in errors)

    def test_ref_missing_title_warning(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=2023, authors=["Smith"], title=None)
        doc = _doc(references=[ref])
        v = DocumentValidator()
        errors, warnings = v._check_references(doc)
        assert any("R1" in w and "title" in w for w in warnings)

    def test_ref_all_fields_ok(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=2023, authors=["Smith"], title="Paper")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        errors, warnings = v._check_references(doc)
        assert errors == []
        assert warnings == []


class TestCheckTables:
    def test_table_with_caption(self):
        from app.models import Table
        tbl = Table(table_id="t1", num_rows=1, num_cols=1,
                     index=0, block_index=0,
                     caption_text="Table 1. Results")
        doc = _doc(tables=[tbl])
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert warnings == []

    def test_table_without_caption(self):
        from app.models import Table
        tbl = Table(table_id="t1", num_rows=1, num_cols=1,
                     index=0, block_index=0,
                     caption_text=None)
        doc = _doc(tables=[tbl])
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert any("missing caption" in w for w in warnings)

    def test_empty_table_attr(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert warnings == []


class TestCheckReferenceIntegrity:
    def test_no_references(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_reference_integrity(doc)
        assert errors == []
        assert warnings == []

    def test_valid_doi_high_confidence(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        doi="10.1234/test", title="Paper",
                        year=2023, authors=["Smith"])
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(return_value={"title": "Paper"})
        v.crossref_client.calculate_confidence = MagicMock(return_value=0.85)
        errors, warnings = v._check_reference_integrity(doc)
        assert errors == []
        assert warnings == []
        assert ref.metadata["validation"]["doi_valid"] is True
        assert ref.metadata["validation"]["confidence"] == 0.85

    def test_invalid_doi(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        doi="10.1234/bad")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=False)
        errors, warnings = v._check_reference_integrity(doc)
        assert any("invalid DOI" in w for w in warnings)
        assert ref.metadata["validation"]["doi_valid"] is False
        assert ref.metadata["validation"]["confidence"] == 0.0

    def test_low_confidence_warning(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        doi="10.1234/low", title="Paper",
                        year=2023, authors=["Smith"])
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(return_value={"title": "Other"})
        v.crossref_client.calculate_confidence = MagicMock(return_value=0.3)
        errors, warnings = v._check_reference_integrity(doc)
        assert any("low confidence" in w for w in warnings)

    def test_metadata_fetch_exception(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        doi="10.1234/test")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(side_effect=ConnectionError("timeout"))
        errors, warnings = v._check_reference_integrity(doc)
        assert any("Failed to fetch metadata" in w for w in warnings)

    def test_validate_doi_exception(self):
        from app.models import Reference
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        doi="10.1234/test")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(side_effect=ValueError("bad request"))
        errors, warnings = v._check_reference_integrity(doc)
        assert any("CrossRef validation failed" in w for w in warnings)

    def test_method_level_crash_safe_function_fallback(self):
        from app.models import Reference
        v = DocumentValidator()
        doc = MagicMock()
        # Accessing doc.references raises to trigger safe_function decorator
        type(doc).references = PropertyMock(side_effect=RuntimeError("boom"))
        errors, warnings = v._check_reference_integrity(doc)
        assert any("CrossRef validation skipped" in w for w in warnings)


class TestValidateDocument:
    def test_convenience_function(self):
        doc = _doc()
        result = validate_document(doc)
        assert isinstance(result, ValidationResult)

    def test_convenience_function_safe_fallback(self):
        doc = _doc()
        with patch("app.pipeline.validation.validator_v3.DocumentValidator") as m_cls:
            m_cls.return_value.validate.side_effect = RuntimeError("boom")
            result = validate_document(doc)
        assert result.is_valid is False
        assert "crashed" in result.errors[0]


# ===========================================================================
# ReviewManager
# ===========================================================================

class TestReviewManagerInit:
    def test_default_thresholds(self):
        rm = ReviewManager()
        assert rm.review_threshold == 0.70
        assert rm.critical_threshold == 0.45

    def test_custom_thresholds(self):
        rm = ReviewManager(review_threshold=0.8, critical_threshold=0.3)
        assert rm.review_threshold == 0.8
        assert rm.critical_threshold == 0.3

    def test_critical_gte_review_raises(self):
        with pytest.raises(ValueError, match="critical_threshold"):
            ReviewManager(review_threshold=0.5, critical_threshold=0.5)

    def test_out_of_range_thresholds(self):
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(review_threshold=1.5, critical_threshold=0.3)
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(review_threshold=0.5, critical_threshold=-0.1)


class TestReviewManagerEvaluate:
    def make_doc(self, blocks=None):
        doc = _doc(blocks=blocks or [])
        return doc

    def test_all_high_confidence_ok(self):
        b = _block(classification_confidence=0.95, semantic_intent="ABSTRACT")
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK
        assert doc.review.lowest_confidence == 0.95

    def test_critical_confidence(self):
        b = _block(classification_confidence=0.3, semantic_intent="METHODS")
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.CRITICAL
        assert any("CRITICAL" in f for f in doc.review.flags)

    def test_review_confidence(self):
        b = _block(classification_confidence=0.55, semantic_intent="RESULTS")
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.REVIEW
        assert any("REVIEW" in f for f in doc.review.flags)
        # Should not have CRITICAL flags
        assert not any("CRITICAL" in f for f in doc.review.flags)

    def test_none_confidence_fallsback_to_1(self):
        b = _block(classification_confidence=None)
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_confidence_from_metadata_classification(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"classification_confidence": 0.35})
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.CRITICAL

    def test_confidence_from_metadata_nlp(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"nlp_confidence": 0.55})
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.REVIEW

    def test_non_numeric_confidence_defaults_to_1(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"classification_confidence": "bad"})
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_confidence_clamped(self):
        b = _block(classification_confidence=1.5)
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.lowest_confidence <= 1.0

    def test_semantic_intent_fallback(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"semantic_intent": "ACKNOWLEDGMENTS"},
                  classification_confidence=0.3)
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert any("ACKNOWLEDGMENTS" in f for f in doc.review.flags)

    def test_semantic_advice_low_confidence(self):
        b = _block(classification_confidence=0.95)
        doc = self.make_doc(blocks=[b])
        doc.metadata.ai_hints = {"semantic_advice": {"confidence": 0.5}}
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.REVIEW

    def test_semantic_advice_higher_ignored(self):
        b = _block(classification_confidence=0.95)
        doc = self.make_doc(blocks=[b])
        doc.metadata.ai_hints = {"semantic_advice": {"confidence": 0.9}}
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_flags_limited_to_5(self):
        blocks = [_block(block_id=f"b{i}", classification_confidence=0.3,
                         semantic_intent=f"S{i}") for i in range(10)]
        doc = self.make_doc(blocks=blocks)
        rm = ReviewManager()
        rm.evaluate(doc)
        assert len(doc.review.flags) <= 5

    def test_lowest_conf_tracked_across_blocks(self):
        b1 = _block(classification_confidence=0.9)
        b2 = _block(classification_confidence=0.4)
        doc = self.make_doc(blocks=[b1, b2])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.lowest_confidence == 0.4
        assert doc.review.status == ReviewStatus.CRITICAL

    def test_reason_set_for_critical(self):
        b = _block(classification_confidence=0.3)
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.reason is not None

    def test_reason_set_for_review(self):
        b = _block(classification_confidence=0.55)
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.reason is not None

    def test_no_flags_for_ok(self):
        b = _block(classification_confidence=0.95)
        doc = self.make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.flags == []


# ===========================================================================
# AIExplainer
# ===========================================================================

class TestAIExplainer:
    def test_explain_empty_errors(self):
        explainer = AIExplainer()
        result = explainer.explain_results({"errors": []})
        assert result == []

    def test_explain_missing_section_string_error(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Missing required section: Abstract"]
        })
        assert len(result) == 1
        assert "missing" in result[0].lower()
        assert "IEEE" in result[0]

    def test_explain_reference_string_error(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Reference R1 missing DOI"]
        })
        assert len(result) == 1
        assert "reference" in result[0].lower()

    def test_explain_general_string_error(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Formatting issue detected"]
        })
        assert len(result) == 1
        assert "formatting error" in result[0]

    def test_explain_dict_error(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [{"category": "figure_captions", "message": "Fig 1 missing caption"}]
        })
        assert len(result) == 1
        assert "Figures detected" in result[0]

    def test_explain_dict_error_unknown_category(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [{"category": "unknown_category", "message": "Something is off"}]
        })
        assert len(result) == 1
        assert "formatting error" in result[0].lower()

    def test_explain_custom_publisher(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Missing required section: Abstract"]
        }, publisher="ACM")
        assert "ACM" in result[0]

    def test_explain_multiple_errors(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [
                "Missing required section: Abstract",
                {"category": "figure_captions", "message": "Fig 1 missing caption"},
                "Formatting issue detected"
            ]
        })
        assert len(result) == 3

    def test_explain_no_errors_key(self):
        explainer = AIExplainer()
        result = explainer.explain_results({})
        assert result == []
