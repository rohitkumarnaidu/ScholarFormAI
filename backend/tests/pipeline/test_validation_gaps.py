
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime
import pytest

from app.models import (
)
from app.pipeline.validation.validator_v3 import (
    DocumentValidator, ValidationResult, validate_document
from app.pipeline.validation.review_manager import ReviewManager
from app.pipeline.validation.ai_explainer import AIExplainer
    from app.models import (
    return PipelineDocument(document_id="test-123", **overrides)


def _block(block_id="b1", index=0, text="Hello", **kw) -> Block:
    return Block(block_id=block_id, index=index, text=text, **kw)


# ===========================================================================
# DocumentValidator - __init__ gap coverage
# ===========================================================================

class TestDocumentValidatorInitGaps:
    """Lines 44-47: __init__ dependencies."""

    def test_init_contract_loader(self):
        v = DocumentValidator()
        assert v.contract_loader is not None
        assert v.order_validator is not None
        assert v.integrity_engine is not None
        assert v.crossref_client is not None

    def test_init_with_custom_contracts_dir(self):
        """Custom contracts_dir parameter."""
        v = DocumentValidator(contracts_dir="/custom/path")
        assert v.contract_loader is not None


# ===========================================================================
# DocumentValidator - _as_bool gap coverage
# ===========================================================================

class TestAsBoolGaps:
    """Lines 51-63: remaining _as_bool branches."""

    def test_none_with_false_default(self):
        assert DocumentValidator._as_bool(None) is False

    def test_none_with_true_default(self):
        assert DocumentValidator._as_bool(None, True) is True

    def test_bool_passthrough_true(self):
        assert DocumentValidator._as_bool(True) is True

    def test_bool_passthrough_false(self):
        assert DocumentValidator._as_bool(False) is False

    def test_int_one(self):
        assert DocumentValidator._as_bool(1) is True

    def test_int_zero(self):
        assert DocumentValidator._as_bool(0) is False

    def test_float_one(self):
        assert DocumentValidator._as_bool(1.0) is True

    def test_float_zero(self):
        assert DocumentValidator._as_bool(0.0) is False

    def test_string_true_variants(self):
        assert DocumentValidator._as_bool("true") is True
        assert DocumentValidator._as_bool("True") is True
        assert DocumentValidator._as_bool("yes") is True
        assert DocumentValidator._as_bool("1") is True
        assert DocumentValidator._as_bool("on") is True

    def test_string_false_variants(self):
        assert DocumentValidator._as_bool("false") is False
        assert DocumentValidator._as_bool("False") is False
        assert DocumentValidator._as_bool("no") is False
        assert DocumentValidator._as_bool("0") is False
        assert DocumentValidator._as_bool("off") is False

    def test_string_unrecognized_returns_default(self):
        assert DocumentValidator._as_bool("maybe") is False
        assert DocumentValidator._as_bool("maybe", True) is True


# ===========================================================================
# DocumentValidator - process gap coverage
# ===========================================================================

class TestProcessGaps:
    """Lines 67-69: process with safe_execution."""

    def test_process_calls_validate(self):
        doc = _doc()
        v = DocumentValidator()
        v.validate = MagicMock(return_value=ValidationResult(is_valid=True))
        result = v.process(doc)
        v.validate.assert_called_once_with(doc)
        assert result is doc

    def test_process_validate_crash_still_returns_doc(self):
        doc = _doc()
        v = DocumentValidator()
        v.validate = MagicMock(side_effect=RuntimeError("crash"))
        result = v.process(doc)
        assert result is doc


# ===========================================================================
# DocumentValidator - validate gap coverage (lines 79-143)
# ===========================================================================

class TestValidateGaps:
    """Full validate method coverage."""

    def _make_validator(self, check_results=None):
        v = DocumentValidator()
        if check_results is None:
            check_results = {
                "_check_sections": ([], []),
                "_check_figures": ([], []),
                "_check_references": ([], []),
                "_check_tables": ([], []),
                "_check_reference_integrity": ([], []),
            }
        for method_name, (errs, warns) in check_results.items():
            setattr(v, method_name, MagicMock(return_value=(errs, warns)))
        v.integrity_engine.validate_integrity = MagicMock(return_value=[])
        v.review_manager = MagicMock()
        return v

    def test_validate_clean_document(self):
        doc = _doc()
        v = self._make_validator()
        result = v.validate(doc)
        assert result.is_valid is True
        assert doc.is_valid is True
        assert doc.validation_errors == []
        assert doc.validation_warnings == []

    def test_validate_with_section_errors(self):
        doc = _doc()
        v = self._make_validator({"_check_sections": (["Missing Abstract"], [])})
        result = v.validate(doc)
        assert result.is_valid is False
        assert "Missing Abstract" in doc.validation_errors

    def test_validate_with_figure_warnings(self):
        doc = _doc()
        v = self._make_validator({"_check_figures": ([], ["Figure f1 missing caption"])})
        result = v.validate(doc)
        assert "Figure f1 missing caption" in doc.validation_warnings

    def test_validate_with_reference_errors(self):
        doc = _doc()
        v = self._make_validator({"_check_references": (["Ref r1 missing authors"], ["Ref r1 missing year"])})
        result = v.validate(doc)
        assert "Ref r1 missing authors" in doc.validation_errors
        assert "Ref r1 missing year" in doc.validation_warnings

    def test_validate_with_table_warnings(self):
        doc = _doc()
        v = self._make_validator({"_check_tables": ([], ["Table 1 missing caption"])})
        result = v.validate(doc)
        assert "Table 1 missing caption" in doc.validation_warnings

    def test_validate_integrity_dangling_error(self):
        doc = _doc()
        v = self._make_validator()
        v.integrity_engine.validate_integrity = MagicMock(return_value=["Dangling reference to Fig. 1"])
        result = v.validate(doc)
        assert "Dangling reference to Fig. 1" in result.errors

    def test_validate_integrity_warning(self):
        doc = _doc()
        v = self._make_validator()
        v.integrity_engine.validate_integrity = MagicMock(return_value=["Warning: figure out of order"])
        result = v.validate(doc)
        assert "Warning: figure out of order" in result.warnings

    def test_validate_fast_mode_skips_doi(self):
        doc = _doc(formatting_options={"fast_mode": True})
        v = self._make_validator()
        result = v.validate(doc)
        assert result.is_valid is True

    def test_validate_doi_checks_in_non_fast(self):
        doc = _doc()
        v = DocumentValidator()
        v._check_sections = MagicMock(return_value=([], []))
        v._check_figures = MagicMock(return_value=([], []))
        v._check_references = MagicMock(return_value=([], []))
        v._check_tables = MagicMock(return_value=([], []))
        v._check_reference_integrity = MagicMock(return_value=(["DOI warning"], []))
        v.integrity_engine.validate_integrity = MagicMock(return_value=[])
        v.review_manager = MagicMock()
        result = v.validate(doc)
        assert "DOI warning" in doc.validation_warnings

    def test_validate_adds_processing_stage(self):
        doc = _doc()
        v = self._make_validator()
        v.validate(doc)
        assert len(doc.processing_history) >= 1
        stage = doc.processing_history[-1]
        assert stage.stage_name == "validation"

    def test_validate_returns_stats(self):
        doc = _doc()
        v = self._make_validator()
        result = v.validate(doc)
        assert "blocks" in result.stats
        assert "figures" in result.stats

    def test_validate_with_reference_integrity_warnings(self):
        """DOI warnings are also added to validation_warnings."""
        doc = _doc()
        v = DocumentValidator()
        v._check_sections = MagicMock(return_value=([], []))
        v._check_figures = MagicMock(return_value=([], []))
        v._check_references = MagicMock(return_value=([], []))
        v._check_tables = MagicMock(return_value=([], []))
        v._check_reference_integrity = MagicMock(return_value=(["DOI error"], []))
        v.integrity_engine.validate_integrity = MagicMock(return_value=[])
        v.review_manager = MagicMock()
        v.validate(doc)
        assert "DOI error" in doc.validation_warnings


# ===========================================================================
# DocumentValidator - _check_sections gap coverage (lines 151-175)
# ===========================================================================

class TestCheckSectionsGaps:
    """Full _check_sections coverage."""

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

    def test_template_name_extracted_for_publisher(self):
        doc = _doc(blocks=[_block(section_name="Intro")],
                   template=TemplateInfo(template_name="ACM"))
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "ACM")

    def test_no_template_fallback_to_ieee(self):
        doc = _doc(blocks=[_block(section_name="Intro")])
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "IEEE")

    def test_template_without_name_fallback(self):
        doc = _doc(blocks=[_block(section_name="Intro")])
        doc.template = MagicMock()
        del doc.template.template_name
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "IEEE")

    def test_template_access_exception_fallback(self):
        doc = _doc(blocks=[_block(section_name="Intro")])
        doc.template = MagicMock()
        del doc.template.template_name
        v = DocumentValidator()
        v.order_validator.validate_order = MagicMock(return_value=[])
        errors, warnings = v._check_sections(doc)
        v.order_validator.validate_order.assert_called_with(doc, "IEEE")


# ===========================================================================
# DocumentValidator - _check_figures gap coverage (lines 178-185)
# ===========================================================================

class TestCheckFiguresGaps:
    """Full _check_figures coverage."""

    def test_figure_with_caption(self):
        fig = Figure(figure_id="f1", index=0, caption_text="Fig. 1. Results")
        doc = _doc(figures=[fig])
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert errors == []
        assert warnings == []

    def test_figure_without_caption(self):
        fig = Figure(figure_id="F1", index=0, caption_text=None)
        doc = _doc(figures=[fig])
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert "Figure F1 missing caption" in warnings

    def test_figure_with_empty_caption(self):
        fig = Figure(figure_id="F2", index=1, caption_text="")
        doc = _doc(figures=[fig])
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert "Figure F2 missing caption" in warnings

    def test_no_figures(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert errors == []
        assert warnings == []

    def test_multiple_figures_some_missing_captions(self):
        figs = [
        ]
        doc = _doc(figures=figs)
        v = DocumentValidator()
        errors, warnings = v._check_figures(doc)
        assert "Figure f2 missing caption" in warnings
        assert len(warnings) == 1


# ===========================================================================
# DocumentValidator - _check_references gap coverage (lines 188-211)
# ===========================================================================

class TestCheckReferencesGaps:
    """Full _check_references coverage."""

    def test_no_references_no_section(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=["Introduction"]):
            errors, warnings = v._check_references(doc)
            assert errors == []
            assert warnings == []

    def test_no_references_but_section_exists(self):
        doc = _doc()
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=["References"]):
            errors, warnings = v._check_references(doc)
            assert "References section found but no reference entries parsed" in warnings

    def test_ref_missing_year(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=None, authors=["Smith"], title="Paper")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=[]):
            errors, warnings = v._check_references(doc)
            assert any("R1" in w and "year" in w for w in warnings)

    def test_ref_missing_authors_error(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=2023, authors=[], title="Paper")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=[]):
            errors, warnings = v._check_references(doc)
            assert any("R1" in e and "authors" in e for e in errors)

    def test_ref_missing_title_warning(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=2023, authors=["Smith"], title=None)
        doc = _doc(references=[ref])
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=[]):
            errors, warnings = v._check_references(doc)
            assert any("R1" in w and "title" in w for w in warnings)

    def test_ref_all_fields_ok(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref text", index=0,
                        year=2023, authors=["Smith"], title="Paper")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=[]):
            errors, warnings = v._check_references(doc)
            assert errors == []
            assert warnings == []

    def test_multiple_references_mixed_issues(self):
        refs = [
                      raw_text="Ref1", index=0, year=None, authors=[], title=None),
                      raw_text="Ref2", index=1, year=2023, authors=["Smith"], title="Paper"),
        ]
        doc = _doc(references=refs)
        v = DocumentValidator()
        with patch.object(PipelineDocument, "get_section_names", return_value=[]):
            errors, warnings = v._check_references(doc)
            assert any("R1" in e for e in errors)
            assert any("R1" in w for w in warnings)


# ===========================================================================
# DocumentValidator - _check_tables gap coverage (lines 214-220)
# ===========================================================================

class TestCheckTablesGaps:
    """Full _check_tables coverage."""

    def test_table_with_caption(self):
        tbl = Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0,
                    caption_text="Table 1. Results")
        doc = _doc(tables=[tbl])
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert warnings == []

    def test_table_without_caption(self):
        tbl = Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0,
                    caption_text=None)
        doc = _doc(tables=[tbl])
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert any("missing caption" in w for w in warnings)

    def test_table_empty_caption(self):
        tbl = Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=0,
                    caption_text="")
        doc = _doc(tables=[tbl])
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert any("missing caption" in w for w in warnings)

    def test_no_tables(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert warnings == []

    def test_document_without_tables_attr(self):
        doc = _doc()
        del doc.tables
        v = DocumentValidator()
        errors, warnings = v._check_tables(doc)
        assert warnings == []


# ===========================================================================
# DocumentValidator - _check_reference_integrity gap coverage (lines 227-269)
# ===========================================================================

class TestCheckReferenceIntegrityGaps:
    """Full _check_reference_integrity coverage."""

    def test_no_references(self):
        doc = _doc()
        v = DocumentValidator()
        errors, warnings = v._check_reference_integrity(doc)
        assert errors == []
        assert warnings == []

    def test_reference_without_doi_skipped(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0, doi=None)
        doc = _doc(references=[ref])
        v = DocumentValidator()
        errors, warnings = v._check_reference_integrity(doc)
        assert errors == []
        assert warnings == []

    def test_valid_doi_high_confidence(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0,
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
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0, doi="10.1234/bad")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=False)
        errors, warnings = v._check_reference_integrity(doc)
        assert any("invalid DOI" in w for w in warnings)
        assert ref.metadata["validation"]["doi_valid"] is False
        assert ref.metadata["validation"]["confidence"] == 0.0

    def test_low_confidence_warning(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0,
                        doi="10.1234/low", title="Paper",
                        year=2023, authors=["Smith"])
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(return_value={"title": "Other"})
        v.crossref_client.calculate_confidence = MagicMock(return_value=0.3)
        errors, warnings = v._check_reference_integrity(doc)
        assert any("low confidence" in w for w in warnings)

    def test_confidence_exactly_at_threshold(self):
        """Confidence == 0.5 is NOT below threshold, so no low confidence warning."""
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0,
                        doi="10.1234/test", title="Paper",
                        year=2023, authors=["Smith"])
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(return_value={"title": "Paper"})
        v.crossref_client.calculate_confidence = MagicMock(return_value=0.5)
        errors, warnings = v._check_reference_integrity(doc)
        assert "low confidence" not in " ".join(warnings).lower()

    def test_metadata_fetch_exception(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0, doi="10.1234/test")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(side_effect=ConnectionError("timeout"))
        errors, warnings = v._check_reference_integrity(doc)
        assert any("Failed to fetch metadata" in w for w in warnings)

    def test_validate_doi_exception(self):
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0, doi="10.1234/test")
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(side_effect=ValueError("bad request"))
        errors, warnings = v._check_reference_integrity(doc)
        assert any("CrossRef validation failed" in w for w in warnings)

    def test_safe_function_fallback_on_crash(self):
        """safe_function decorator handles crash and returns fallback."""
        v = DocumentValidator()
        doc = MagicMock()
        type(doc).references = PropertyMock(side_effect=RuntimeError("boom"))
        errors, warnings = v._check_reference_integrity(doc)
        assert any("CrossRef validation skipped" in w for w in warnings)

    def test_existing_validation_metadata_not_overwritten(self):
        """Existing metadata validation dict is preserved."""
        ref = Reference(reference_id="r1", citation_key="R1",
                        raw_text="Ref", index=0,
                        doi="10.1234/test", title="Paper",
                        year=2023, authors=["Smith"],
                        metadata={"existing": "value"})
        doc = _doc(references=[ref])
        v = DocumentValidator()
        v.crossref_client.validate_doi = MagicMock(return_value=True)
        v.crossref_client.get_metadata = MagicMock(return_value={"title": "Paper"})
        v.crossref_client.calculate_confidence = MagicMock(return_value=0.95)
        errors, warnings = v._check_reference_integrity(doc)
        assert ref.metadata["existing"] == "value"
        assert ref.metadata["validation"]["crossref_checked"] is True


# ===========================================================================
# validate_document convenience function (lines 278-279)
# ===========================================================================

class TestValidateDocumentConvenience:
    """Cover validate_document function."""

    def test_convenience_function_returns_result(self):
        doc = _doc()
        result = validate_document(doc)
        assert isinstance(result, ValidationResult)

    def test_convenience_function_with_crash(self):
        doc = _doc()
        with patch("app.pipeline.validation.validator_v3.DocumentValidator") as m_cls:
            m_cls.return_value.validate.side_effect = RuntimeError("crash")
            result = validate_document(doc)
        assert result.is_valid is False
        assert "crashed" in result.errors[0]


# ===========================================================================
# ReviewManager - __init__ gap coverage (lines 17-27)
# ===========================================================================

class TestReviewManagerInitGaps:
    """Lines 17-27: full __init__ validation."""

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

    def test_critical_greater_than_review_raises(self):
        with pytest.raises(ValueError, match="critical_threshold"):
            ReviewManager(review_threshold=0.3, critical_threshold=0.8)

    def test_threshold_out_of_range_high_critical(self):
        with pytest.raises(ValueError, match="must be less than"):
            ReviewManager(review_threshold=0.5, critical_threshold=1.5)

    def test_threshold_out_of_range_low_critical(self):
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(review_threshold=0.5, critical_threshold=-0.1)

    def test_threshold_out_of_range_high_review(self):
        with pytest.raises(ValueError, match="Thresholds must be between"):
            ReviewManager(review_threshold=1.5, critical_threshold=0.3)

    def test_threshold_out_of_range_low_review(self):
        with pytest.raises(ValueError, match="must be less than"):
            ReviewManager(review_threshold=-0.1, critical_threshold=0.3)

    def test_threshold_boundary_valid(self):
        """Boundary values should work."""
        rm = ReviewManager(review_threshold=1.0, critical_threshold=0.0)
        assert rm.review_threshold == 1.0
        assert rm.critical_threshold == 0.0


# ===========================================================================
# ReviewManager - evaluate gap coverage (lines 34-119)
# ===========================================================================

class TestReviewManagerEvaluateGaps:
    """Full evaluate method coverage."""

    def _make_doc(self, blocks=None, ai_hints=None):
        doc = PipelineDocument(document_id="test", blocks=blocks or [])
        if ai_hints:
            doc.metadata.ai_hints = ai_hints
        else:
            doc.metadata.ai_hints = {}
        return doc

    def test_no_blocks_ok(self):
        doc = self._make_doc(blocks=[])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK
        assert doc.review.lowest_confidence == 1.0
        assert doc.review.flags == []

    def test_all_high_confidence_ok(self):
        b = _block(classification_confidence=0.95, semantic_intent="ABSTRACT")
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK
        assert doc.review.lowest_confidence == 0.95
        assert doc.review.flags == []

    def test_critical_confidence(self):
        b = _block(classification_confidence=0.3, semantic_intent="METHODS")
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.CRITICAL
        assert any("CRITICAL" in f for f in doc.review.flags)

    def test_review_confidence(self):
        b = _block(classification_confidence=0.55, semantic_intent="RESULTS")
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.REVIEW
        assert any("REVIEW" in f for f in doc.review.flags)
        assert not any("CRITICAL" in f for f in doc.review.flags)

    def test_none_confidence_fallsback_to_1(self):
        b = _block(classification_confidence=None)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_confidence_from_metadata_classification(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"classification_confidence": 0.35})
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.CRITICAL

    def test_confidence_from_metadata_nlp(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"nlp_confidence": 0.55})
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.REVIEW

    def test_non_numeric_confidence_defaults_to_1(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"classification_confidence": "bad"})
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_confidence_clamped_above_1(self):
        b = _block(classification_confidence=1.5)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.lowest_confidence <= 1.0

    def test_confidence_clamped_below_0(self):
        b = _block(classification_confidence=-0.5)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.lowest_confidence >= 0.0

    def test_semantic_intent_from_metadata(self):
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"semantic_intent": "ACKNOWLEDGMENTS"},
                  classification_confidence=0.3)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert any("ACKNOWLEDGMENTS" in f for f in doc.review.flags)

    def test_semantic_intent_fallback(self):
        b = Block(block_id="b1", index=0, text="test",
                  classification_confidence=0.3)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert any("unknown" in f.lower() for f in doc.review.flags)

    def test_semantic_advice_low_confidence(self):
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b], ai_hints={"semantic_advice": {"confidence": 0.5}})
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.REVIEW

    def test_semantic_advice_higher_ignored(self):
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b], ai_hints={"semantic_advice": {"confidence": 0.9}})
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_semantic_advice_lowers_lowest_conf(self):
        """semantic advice confidence < block confidence lowers lowest_conf."""
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b], ai_hints={"semantic_advice": {"confidence": 0.4}})
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.lowest_confidence == 0.4
        assert doc.review.status == ReviewStatus.CRITICAL

    def test_semantic_advice_no_confidence_key(self):
        """Missing confidence in semantic_advice defaults to 1.0."""
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b], ai_hints={"semantic_advice": {}})
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK

    def test_flags_limited_to_5_critical_first(self):
        blocks = [_block(block_id=f"b{i}", classification_confidence=0.3,
                         semantic_intent=f"S{i}") for i in range(10)]
        doc = self._make_doc(blocks=blocks)
        rm = ReviewManager()
        rm.evaluate(doc)
        assert len(doc.review.flags) <= 5
        # All should be CRITICAL since all confidences < critical_threshold
        assert all("CRITICAL" in f for f in doc.review.flags)

    def test_mixed_critical_and_review_flags_prioritized(self):
        b1 = _block(classification_confidence=0.3, semantic_intent="RESULTS")
        b2 = _block(classification_confidence=0.55, semantic_intent="METHODS")
        doc = self._make_doc(blocks=[b1, b2])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.CRITICAL
        flags = doc.review.flags
        # CRITICAL flags come before REVIEW flags
        assert flags[0].startswith("CRITICAL")
        assert flags[-1].startswith("REVIEW")

    def test_lowest_conf_tracked_across_blocks(self):
        b1 = _block(classification_confidence=0.9)
        b2 = _block(classification_confidence=0.4)
        doc = self._make_doc(blocks=[b1, b2])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.lowest_confidence == 0.4

    def test_reason_set_for_critical(self):
        b = _block(classification_confidence=0.3)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.reason is not None
        assert "failed automated" in doc.review.reason.lower()

    def test_reason_set_for_review(self):
        b = _block(classification_confidence=0.55)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.reason is not None
        assert "human verification" in doc.review.reason.lower()

    def test_no_flags_for_ok(self):
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.flags == []
        assert doc.review.reason is None

    def test_evaluate_returns_doc(self):
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        result = rm.evaluate(doc)
        assert result is doc

    def test_review_metadata_assigned(self):
        b = _block(classification_confidence=0.95)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert isinstance(doc.review, ReviewMetadata)
        assert doc.review.status == ReviewStatus.OK
        assert doc.review.lowest_confidence == 0.95

    def test_block_without_classification_confidence(self):
        """Block missing classification_confidence entirely."""
        b = Block(block_id="b1", index=0, text="test")
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK
        assert doc.review.lowest_confidence == 1.0

    def test_confidence_extraction_order(self):
        """metadata.classification_confidence > block attr > metadata.nlp_confidence."""
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"classification_confidence": 0.3, "nlp_confidence": 0.9},
                  classification_confidence=0.95)
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        # Uses metadata.classification_confidence (0.3) first
        assert doc.review.lowest_confidence == 0.3
        assert doc.review.status == ReviewStatus.CRITICAL

    def test_confidence_from_metadata_without_classification_key(self):
        """metadata is dict but has no classification_confidence."""
        b = Block(block_id="b1", index=0, text="test",
                  metadata={"other": "value"})
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert doc.review.status == ReviewStatus.OK
        assert doc.review.lowest_confidence == 1.0

    def test_block_semantic_intent_fallback_to_unknown(self):
        """Block with no semantic_intent attribute or metadata key falls back."""
        b = Block(block_id="b1", index=0, text="test",
                  classification_confidence=0.3)
        b.metadata = {}
        doc = self._make_doc(blocks=[b])
        rm = ReviewManager()
        rm.evaluate(doc)
        assert any("unknown" in f.lower() for f in doc.review.flags)


# ===========================================================================
# AIExplainer gap coverage (lines 14, 25-49)
# ===========================================================================

class TestAIExplainerGaps:
    """Full AIExplainer coverage."""

    def test_init_creates_explanation_map(self):
        """Line 14: explanation_map initialized."""
        explainer = AIExplainer()
        assert "missing_sections" in explainer.explanation_map
        assert "citation_format" in explainer.explanation_map
        assert "figure_captions" in explainer.explanation_map
        assert "reference_completeness" in explainer.explanation_map

    def test_explain_empty_errors(self):
        explainer = AIExplainer()
        result = explainer.explain_results({"errors": []})
        assert result == []

    def test_explain_missing_section_error(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Missing required section: Abstract"]
        })
        assert len(result) == 1
        assert "missing" in result[0].lower()
        assert "IEEE" in result[0]
        assert "Abstract" in result[0]

    def test_explain_reference_error(self):
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

    def test_explain_multiple_errors_different_types(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [
                "Missing required section: Abstract",
                {"category": "figure_captions", "message": "Fig 1 missing caption"},
                "Formatting issue detected",
                {"category": "reference_completeness", "message": "Missing DOI"},
            ]
        })
        assert len(result) == 4

    def test_explain_no_errors_key(self):
        explainer = AIExplainer()
        result = explainer.explain_results({})
        assert result == []

    def test_explain_section_string_error(self):
        """String error containing 'section' triggers missing_sections."""
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": ["Section error in formatting"]
        })
        assert "section" in result[0].lower()

    def test_explain_dict_error_no_message(self):
        """Dict error without message field."""
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [{"category": "figure_captions"}]
        })
        assert len(result) == 1
        assert "Figures detected" in result[0]

    def test_explain_dict_error_citation_format(self):
        explainer = AIExplainer()
        result = explainer.explain_results({
            "errors": [{"category": "citation_format", "message": "Wrong style"}]
        })
        assert len(result) == 1
        assert "citation" in result[0].lower()
