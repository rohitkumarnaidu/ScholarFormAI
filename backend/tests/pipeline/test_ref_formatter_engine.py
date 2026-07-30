# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation
from __future__ import annotations
from unittest.mock import MagicMock, patch, PropertyMock
import pytest
pytestmark = [pytest.mark.pipeline]


@pytest.fixture
def mock_contract_loader():
    cl = MagicMock()
    cl.load.return_value = {
        "references": {
            "style": "ieee",
            "normalization": {
                "journal_format": "{authors}, \"{title},\" {journal}, vol. {volume}, no. {issue}, pp. {pages}, {year}.",
                "conference_format": "{authors}, \"{title},\" in {conference}, {year}.",
                "default_format": "{authors}, {title}, {year}.",
                "max_authors": 3,
                "et_al_suffix": "et al."
            }
        }
    }
    return cl


@pytest.fixture
def mock_csl_engine():
    engine = MagicMock()
    engine.format_references.return_value = ["Formatted ref 1", "Formatted ref 2"]
    return engine


@pytest.fixture
def sample_reference():
    from app.models.reference import Reference, ReferenceType
    return [
        Reference(
            reference_id="ref_1",
            citation_key="Smith2020",
            raw_text="Smith, J. et al. (2020). A study.",
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            authors=["Smith, J.", "Doe, A."],
            title="A study on AI",
            journal="Journal of AI",
            year=2020,
            volume="10",
            issue="2",
            pages="100-110",
            doi="10.1234/test",
            index=0
        ),
        Reference(
            reference_id="ref_2",
            citation_key="Jones2021",
            raw_text="Jones, B. (2021). Another study.",
            reference_type=ReferenceType.CONFERENCE_PAPER,
            authors=["Jones, B."],
            title="Another study",
            conference="AI Conf 2021",
            year=2021,
            index=1
        )
    ]


class TestReferenceFormatterEngineInit:
    def test_init_with_contract_loader(self, mock_contract_loader):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        assert engine.contract_loader is mock_contract_loader
        assert engine.csl_engine is not None

    def test_init_with_custom_csl_engine(self, mock_contract_loader, mock_csl_engine):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        assert engine.csl_engine is mock_csl_engine


class TestReferenceFormatterEngineProcess:
    def test_process_with_template(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.pipeline_document import PipelineDocument, TemplateInfo
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        doc = PipelineDocument(document_id="test", references=sample_reference, template=TemplateInfo(template_name="IEEE"))
        result = engine.process(doc)
        assert result.references[0].formatted_text == "Formatted ref 1"

    def test_process_no_template(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.pipeline_document import PipelineDocument
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        doc = PipelineDocument(document_id="test", references=sample_reference, template=None)
        result = engine.process(doc)
        assert result.references[0].formatted_text is not None


class TestFormatAll:
    def test_format_all_empty(self, mock_contract_loader, mock_csl_engine):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        result = engine.format_all([], "IEEE")
        assert result == []

    def test_format_all_csl_success(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        result = engine.format_all(sample_reference, "IEEE")
        assert result[0].formatted_text == "Formatted ref 1"
        assert result[1].formatted_text == "Formatted ref 2"

    def test_format_all_csl_length_mismatch(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        mock_csl_engine.format_references.return_value = ["Only one"]
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        result = engine.format_all(sample_reference, "IEEE")
        assert result[0].formatted_text is not None
        assert result[0].formatted_text != "Only one"

    def test_format_all_csl_exception(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        mock_csl_engine.format_references.side_effect = Exception("CSL failed")
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader, csl_engine=mock_csl_engine)
        result = engine.format_all(sample_reference, "IEEE")
        assert result[0].formatted_text is not None
        assert "Study" in result[0].formatted_text or "study" in result[0].formatted_text

    def test_format_all_fallback_no_rules(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        mock_csl_engine.format_references.side_effect = Exception("CSL failed")
        cl = MagicMock()
        cl.load.return_value = {"references": {}}
        engine = ReferenceFormatterEngine(contract_loader=cl, csl_engine=mock_csl_engine)
        result = engine.format_all(sample_reference, "IEEE")
        assert result == sample_reference

    def test_format_all_csl_with_style_path(self, mock_contract_loader, mock_csl_engine, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        cl = MagicMock()
        cl.load.return_value = {
            "references": {
                "style": "apa",
                "csl_style_path": "/path/to/apa.csl"
            }
        }
        engine = ReferenceFormatterEngine(contract_loader=cl, csl_engine=mock_csl_engine)
        result = engine.format_all(sample_reference, "APA")
        assert result[0].formatted_text == "Formatted ref 1"


class TestFormatSingle:
    def test_format_single_journal(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, \"{title},\" {journal}, {year}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(sample_reference[0], rules)
        assert "Smith" in result
        assert "AI" in result

    def test_format_single_conference(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"conference_format": "{authors}, \"{title},\" in {conference}, {year}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(sample_reference[1], rules)
        assert "Jones" in result
        assert "Another" in result

    def test_format_single_default(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        from app.models.reference import ReferenceType
        ref.reference_type = ReferenceType.BOOK
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"default_format": "{authors}, {title}, {year}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "Smith" in result

    def test_format_single_max_authors_exceeded(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        ref.authors = ["Smith, J.", "Doe, A.", "Lee, K.", "Wang, L."]
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, \"{title},\" {journal}, {year}.", "max_authors": 2, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "et al" in result

    def test_format_single_no_authors(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        ref.authors = []
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, \"{title},\" {journal}, {year}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "Unknown Author" in result

    def test_format_single_missing_title(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        ref.title = None
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, \"{title},\" {journal}, {year}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "Missing Title" in result

    def test_format_single_missing_year(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        ref.year = None
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, {title}, {journal}, {year}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "n.d." in result

    def test_format_single_template_error(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, {missing_key}", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert result == ref.raw_text

    def test_format_single_with_doi(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        ref.doi = "10.1234/test"
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, {doi}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "doi:" in result

    def test_format_single_journal_from_metadata(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[0]
        ref.journal = None
        ref.metadata["journal_full"] = "Journal of Testing"
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, {journal}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "Testing" in result

    def test_format_single_ref_type_str(self, mock_contract_loader):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        from app.models.reference import Reference
        ref = Reference(reference_id="r1", citation_key="k1", raw_text="raw", index=0, authors=["A"], title="T", year=2022)
        ref.reference_type = "journal_article"
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"journal_format": "{authors}, {title}.", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert "A" in result

    def test_format_single_double_punctuation_fix(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[1]
        ref.authors = ["Jones, B"]
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"conference_format": "{authors}..", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert result == "Jones, B."

    def test_format_single_double_comma_fix(self, mock_contract_loader, sample_reference):
        from app.pipeline.references.formatter_engine import ReferenceFormatterEngine
        ref = sample_reference[1]
        engine = ReferenceFormatterEngine(contract_loader=mock_contract_loader)
        rules = {"conference_format": "{authors},,", "max_authors": 3, "et_al_suffix": "et al."}
        result = engine.format_single(ref, rules)
        assert ",," not in result
