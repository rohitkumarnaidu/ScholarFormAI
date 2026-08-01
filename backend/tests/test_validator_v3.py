from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def doc():
    doc = MagicMock()
    doc.figures = []
    doc.references = []
    doc.tables = []
    doc.blocks = []
    doc.is_valid = True
    doc.validation_errors = []
    doc.validation_warnings = []
    doc.formatting_options = {}
    doc.add_processing_stage = MagicMock()
    doc.get_stats.return_value = {"block_count": 0}
    doc.get_section_names.return_value = []
    doc.template.template_name = "ieee"
    return doc


class TestAsBool:
    def test_none_defaults_false(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(None) is False

    def test_none_with_custom_default(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(None, True) is True

    def test_bool_passthrough(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(True) is True
        assert DocumentValidator._as_bool(False) is False

    def test_int_conversion(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool(1) is True
        assert DocumentValidator._as_bool(0) is False

    def test_string_true_variants(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        for s in ["1", "true", "True", "yes", "on"]:
            assert DocumentValidator._as_bool(s) is True, f"'{s}' should be True"

    def test_string_false_variants(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        for s in ["0", "false", "False", "no", "off"]:
            assert DocumentValidator._as_bool(s) is False, f"'{s}' should be False"

    def test_unrecognized_string_defaults(self):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        assert DocumentValidator._as_bool("maybe") is False


class TestCheckFigures:
    def test_no_figures(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        errors, warnings = validator._check_figures(doc)
        assert errors == []
        assert warnings == []

    def test_figure_missing_caption(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        fig = MagicMock()
        fig.figure_id = "fig_001"
        fig.has_caption.return_value = False
        doc.figures = [fig]
        errors, warnings = validator._check_figures(doc)
        assert "missing caption" in warnings[0]


class TestCheckReferences:
    def test_no_references_no_section(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        doc.references = []
        doc.get_section_names.return_value = ["Introduction"]
        errors, warnings = validator._check_references(doc)
        assert errors == []
        assert warnings == []

    def test_references_section_but_no_entries(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        doc.references = []
        doc.get_section_names.return_value = ["References"]
        errors, warnings = validator._check_references(doc)
        assert any("no reference entries" in w for w in warnings)

    def test_ref_missing_fields(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        ref = MagicMock()
        ref.citation_key = "Smith2020"
        ref.year = None
        ref.authors = []
        ref.title = None
        doc.references = [ref]
        errors, warnings = validator._check_references(doc)
        assert any("missing publication year" in w for w in warnings)
        assert any("missing authors" in e for e in errors)
        assert any("missing title" in w for w in warnings)


class TestCheckTables:
    def test_tables_missing_captions(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        tbl = MagicMock()
        tbl.caption_text = None
        doc.tables = [tbl]
        errors, warnings = validator._check_tables(doc)
        assert any("missing caption" in w for w in warnings)


class TestValidate:
    def test_valid_document(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.order_validator.validate_order.return_value = []
        validator.integrity_engine = MagicMock()
        validator.integrity_engine.validate_integrity.return_value = []
        validator.crossref_client = MagicMock()
        with patch("app.pipeline.validation.validator_v3.ReviewManager") as mock_rm:
            mock_rm.return_value.evaluate.return_value = doc
            result = validator.validate(doc)
        assert result.is_valid is True

    def test_invalid_document_with_errors(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.order_validator.validate_order.return_value = ["Missing required section: Methods"]
        validator.integrity_engine = MagicMock()
        validator.integrity_engine.validate_integrity.return_value = []
        validator.crossref_client = MagicMock()
        with patch("app.pipeline.validation.validator_v3.ReviewManager"):
            result = validator.validate(doc)
        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_fast_mode_skips_crossref(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.order_validator.validate_order.return_value = []
        validator.integrity_engine = MagicMock()
        validator.integrity_engine.validate_integrity.return_value = []
        validator.crossref_client = MagicMock()
        doc.formatting_options = {"fast_mode": True}
        with patch("app.pipeline.validation.validator_v3.ReviewManager"):
            validator.validate(doc)
        validator.crossref_client.validate_doi.assert_not_called()


class TestProcess:
    def test_process_wraps_validate(self, doc):
        from app.pipeline.validation.validator_v3 import DocumentValidator
        validator = DocumentValidator()
        validator.contract_loader = MagicMock()
        validator.order_validator = MagicMock()
        validator.integrity_engine = MagicMock()
        validator.crossref_client = MagicMock()
        with patch.object(validator, "validate"):
            result = validator.process(doc)
        assert result is doc


class TestValidateDocumentConvenience:
    def test_convenience_function(self, doc):
        from app.pipeline.validation.validator_v3 import validate_document
        with patch("app.pipeline.validation.validator_v3.DocumentValidator") as mock_dv:
            instance = mock_dv.return_value
            instance.validate.return_value = MagicMock()
            result = validate_document(doc)
        assert result is not None
