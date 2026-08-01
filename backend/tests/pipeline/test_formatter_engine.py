# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.pipeline.references.formatter_engine import ReferenceFormatterEngine


@pytest.fixture
def mock_contract_loader():

    loader = MagicMock()
    loader.load.return_value = {
        "references": {
            "style": "ieee",
            "normalization": {
                "journal_format": "{authors}, {title}, {journal}, {year}.",
                "default_format": "{authors}, {title}, {year}.",
                "max_authors": 3,
                "et_al_suffix": "et al.",
            },
        }
    }
    return loader

@pytest.fixture
def sample_ref():
    from app.models import Reference, ReferenceType
    return Reference(
        reference_id="r1", citation_key="k1", raw_text="test", index=1,
        number=1, title="Deep Learning",
        authors=["Goodfellow, I.", "Bengio, Y.", "Courville, A."],
        year=2016, journal="MIT Press",
        reference_type=ReferenceType.JOURNAL_ARTICLE,
    )

class TestReferenceFormatterEngine:
    def test_process_calls_format_all(self, mock_contract_loader, sample_ref):
        from app.models import PipelineDocument, TemplateInfo
        mock_csl = MagicMock()
        mock_csl.format_references.return_value = ["[1] Goodfellow, I. et al."]
        engine = ReferenceFormatterEngine(mock_contract_loader, csl_engine=mock_csl)
        doc = PipelineDocument(
            document_id="doc1",
            references=[sample_ref],
            template=TemplateInfo(template_name="ieee"),
        )
        result = engine.process(doc)
        assert result.references[0].formatted_text == "[1] Goodfellow, I. et al."

    def test_format_all_csl_success(self, mock_contract_loader, sample_ref):
        mock_csl = MagicMock()
        mock_csl.format_references.return_value = ["Formatted ref"]
        engine = ReferenceFormatterEngine(mock_contract_loader, csl_engine=mock_csl)
        result = engine.format_all([sample_ref], "ieee")
        assert result[0].formatted_text == "Formatted ref"

    def test_format_all_csl_length_mismatch_raises_fallback(self, mock_contract_loader, sample_ref):
        mock_csl = MagicMock()
        mock_csl.format_references.return_value = ["only one", "extra"]
        engine = ReferenceFormatterEngine(mock_contract_loader, csl_engine=mock_csl)
        result = engine.format_all([sample_ref], "ieee")
        # Should fall back to normalization rules
        assert result[0].formatted_text is not None

    def test_format_all_empty(self, mock_contract_loader):
        engine = ReferenceFormatterEngine(mock_contract_loader)
        result = engine.format_all([], "ieee")
        assert result == []

    def test_format_single_journal(self, mock_contract_loader, sample_ref):
        engine = ReferenceFormatterEngine(mock_contract_loader)
        rules = mock_contract_loader.load.return_value["references"]["normalization"]
        result = engine.format_single(sample_ref, rules)
        assert "Goodfellow" in result
        assert "Deep Learning" in result
        assert "MIT Press" in result

    def test_format_single_default(self, mock_contract_loader):
        from app.models import Reference, ReferenceType
        engine = ReferenceFormatterEngine(mock_contract_loader)
        ref = Reference(
            reference_id="r2", citation_key="k2", raw_text="test", index=2,
            title="A Book", authors=["Smith, J."], year=2020,
            reference_type=ReferenceType.BOOK,
        )
        rules = mock_contract_loader.load.return_value["references"]["normalization"]
        result = engine.format_single(ref, rules)
        assert result is not None

    def test_format_single_et_al(self, mock_contract_loader):
        from app.models import Reference, ReferenceType
        engine = ReferenceFormatterEngine(mock_contract_loader)
        ref = Reference(
            reference_id="r3", citation_key="k3", raw_text="test", index=3,
            title="Many Authors", authors=[f"Author {i}" for i in range(10)],
            year=2020, reference_type=ReferenceType.JOURNAL_ARTICLE,
        )
        rules = mock_contract_loader.load.return_value["references"]["normalization"]
        rules["max_authors"] = 2
        result = engine.format_single(ref, rules)
        assert "et al." in result

    def test_format_single_fallback_on_template_error(self, mock_contract_loader):
        from app.models import Reference
        engine = ReferenceFormatterEngine(mock_contract_loader)
        ref = Reference(
            reference_id="r4", citation_key="k4", raw_text="raw fallback", index=4,
        )
        rules = {"journal_format": "{missing_field}", "default_format": "{missing_field}"}
        result = engine.format_single(ref, rules)
        assert result == "raw fallback"

    def test_format_all_csl_fallback_no_rules(self, mock_contract_loader):
        from app.models import Reference
        loader = MagicMock()
        loader.load.return_value = {"references": {}}
        mock_csl = MagicMock()
        mock_csl.format_references.side_effect = Exception("CSL failed")
        engine = ReferenceFormatterEngine(loader, csl_engine=mock_csl)
        ref = Reference(
            reference_id="r1", citation_key="k1", raw_text="test", index=1,
        )
        result = engine.format_all([ref], "ieee")
        assert result[0].formatted_text is None
