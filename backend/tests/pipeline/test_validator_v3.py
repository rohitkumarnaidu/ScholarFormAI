# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestDocumentValidator:
    def _make_doc(self, blocks=None, figures=None, tables=None, references=None, template=None, formatting_options=None):
        doc = MagicMock()
        doc.blocks = blocks or []
        doc.figures = figures or []
        doc.tables = tables or []
        doc.equations = []
        doc.references = references or []
        doc.template = template
        doc.formatting_options = formatting_options or {}
        doc.is_valid = True
        doc.validation_errors = []
        doc.validation_warnings = []
        doc.metadata = MagicMock()
        doc.metadata.ai_hints = {}
        doc.add_processing_stage = MagicMock()
        doc.get_stats = MagicMock(return_value={})
        doc.get_section_names = MagicMock(return_value=set())
        return doc

    def _make_ref(self, citation_key="ref1", year="2024", authors="Alice", title="Paper", has_doi=False, doi=""):
        ref = MagicMock()
        ref.citation_key = citation_key
        ref.year = year
        ref.authors = authors
        ref.title = title
        ref.has_doi.return_value = has_doi
        ref.doi = doi
        ref.metadata = {}
        return ref

    def test_as_bool_various_inputs(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        assert dv._as_bool(None) is False
        assert dv._as_bool(True) is True
        assert dv._as_bool(1) is True
        assert dv._as_bool(0) is False
        assert dv._as_bool("true") is True
        assert dv._as_bool("false") is False
        assert dv._as_bool("yes") is True
        assert dv._as_bool("no") is False
        assert dv._as_bool("random") is False

    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_sections", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_figures", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_references", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_tables", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[])
    def test_validate_success(self, mock_int, mock_tbl, mock_ref, mock_fig, mock_sec):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator()
        doc = self._make_doc()
        result = dv.validate(doc)
        assert result.is_valid is True
        assert result.errors == []

    def test_validate_with_section_errors(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        with patch.object(DocumentValidator, "_check_sections", return_value=(["Missing required section"], [])), \
             patch.object(DocumentValidator, "_check_figures", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_references", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_tables", return_value=([], [])), \
             patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[]):
            dv = DocumentValidator()
            doc = self._make_doc()
            result = dv.validate(doc)
            assert result.is_valid is False
            assert len(result.errors) == 1

    @patch("app.pipeline.validation.validator_v3.ReviewManager.evaluate")
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_sections", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_figures", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_references", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_tables", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[])
    def test_review_manager_called(self, mock_int, mock_tbl, mock_ref, mock_fig, mock_sec, mock_review):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator()
        doc = self._make_doc()
        dv.validate(doc)
        mock_review.assert_called_once()

    def test_check_figures_no_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        fig = MagicMock()
        fig.figure_id = "f1"
        fig.has_caption.return_value = False
        doc = self._make_doc(figures=[fig])
        errs, warns = dv._check_figures(doc)
        assert len(warns) == 1
        assert "Figure f1" in warns[0]

    def test_check_figures_with_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        fig = MagicMock()
        fig.figure_id = "f2"
        fig.has_caption.return_value = True
        doc = self._make_doc(figures=[fig])
        errs, warns = dv._check_figures(doc)
        assert warns == []

    def test_check_references_empty_with_section(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        doc = self._make_doc(references=[])
        doc.get_section_names.return_value = {"references"}
        errs, warns = dv._check_references(doc)
        assert len(warns) == 1
        assert "no reference entries" in warns[0].lower()

    def test_check_references_missing_fields(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        ref = self._make_ref(year=None, authors="", title=None)
        doc = self._make_doc(references=[ref])
        errs, warns = dv._check_references(doc)
        assert len(errs) == 1
        assert "missing authors" in errs[0].lower()

    def test_check_tables_missing_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        tbl = MagicMock()
        tbl.caption_text = None
        doc = self._make_doc(tables=[tbl])
        errs, warns = dv._check_tables(doc)
        assert len(warns) == 1
        assert "missing caption" in warns[0].lower()

    def test_check_tables_with_caption(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator.__new__(DocumentValidator)
        tbl = MagicMock()
        tbl.caption_text = "Table 1: Data"
        doc = self._make_doc(tables=[tbl])
        errs, warns = dv._check_tables(doc)
        assert warns == []

    def test_fast_mode_skips_doi_checks(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator()
        doc = self._make_doc(formatting_options={"fast_mode": True})
        with patch.object(DocumentValidator, "_check_sections", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_figures", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_references", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_tables", return_value=([], [])), \
             patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[]), \
             patch.object(DocumentValidator, "_check_reference_integrity") as mock_doi:
            dv.validate(doc)
            mock_doi.assert_not_called()

    def test_process_calls_validate(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator()
        doc = self._make_doc()
        with patch.object(DocumentValidator, "_check_sections", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_figures", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_references", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_tables", return_value=([], [])), \
             patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[]), \
             patch.object(DocumentValidator, "_check_reference_integrity", return_value=([], [])):
            result = dv.process(doc)
            assert result is doc

    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_sections", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_figures", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_references", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.DocumentValidator._check_tables", return_value=([], []))
    @patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[])
    def test_document_validated_flag_set(self, mock_int, mock_tbl, mock_ref, mock_fig, mock_sec):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        dv = DocumentValidator()
        doc = self._make_doc()
        dv.validate(doc)
        assert doc.is_valid is True

    def test_validate_document_convenience(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator, validate_document
        doc = self._make_doc()
        with patch.object(DocumentValidator, "_check_sections", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_figures", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_references", return_value=([], [])), \
             patch.object(DocumentValidator, "_check_tables", return_value=([], [])), \
             patch("app.pipeline.validation.validator_v3.CrossReferenceEngine.validate_integrity", return_value=[]):
            result = validate_document(doc)
            assert isinstance(result.is_valid, bool)
