# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
import pytest
from pathlib import Path
from app.pipeline.services.csl_engine import CSLEngine

@pytest.fixture
def engine():
    # templates live at backend/app/templates/

    from app.models import Reference, ReferenceType
    return CSLEngine(templates_dir=str(Path(__file__).resolve().parent.parent.parent / "app" / "templates"))

@pytest.fixture
def sample_ref():
    from app.models import Reference, ReferenceType
    return Reference(
        reference_id="ref1",
        citation_key="key1",
        raw_text="test",
        index=1,
        title="Deep Learning",
        authors=["Goodfellow, Ian", "Bengio, Yoshua"],
        year=2016,
        journal="MIT Press",
        publisher="MIT Press",
        volume="1",
        pages="1-800",
        doi="10.1234/dl",
        reference_type=ReferenceType.BOOK,
    )

class TestCSLEngineCapabilities:
    def test_get_capabilities(self, engine):
        from app.models import Reference, ReferenceType
        caps = engine.get_capabilities()
        assert "supports_citeproc" in caps
        assert "supports_external_csl_files" in caps
        assert "estimated_available_styles" in caps

    def test_supports_10k_plus_styles(self, engine):
        from app.models import Reference, ReferenceType
        assert engine.supports_10k_plus_styles() is True

class TestCSLEngineResolveStylePath:
    def test_default_ieee_path(self, engine):
        from app.models import Reference, ReferenceType
        path = engine.resolve_style_path("ieee")
        assert isinstance(path, Path)

    def test_default_apa_path(self, engine):
        from app.models import Reference, ReferenceType
        path = engine.resolve_style_path("apa")
        assert isinstance(path, Path)

    def test_unknown_style_raises(self, engine):
        from app.models import Reference, ReferenceType
        with pytest.raises(FileNotFoundError):
            engine.resolve_style_path("unknown_style_xyz")

class TestCSLEngineToCslName:
    def test_comma_separated(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._to_csl_name("Smith, John")
        assert result["family"] == "Smith"
        assert result["given"] == "John"

    def test_space_separated(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._to_csl_name("John Smith")
        assert result["family"] == "Smith"
        assert result["given"] == "John"

    def test_single_name(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._to_csl_name("Aristotle")
        assert result["literal"] == "Aristotle"

    def test_empty_name(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._to_csl_name("")
        assert result["literal"] == "Unknown Author"

    def test_only_spaces(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._to_csl_name("   ")
        assert result["literal"] == "Unknown Author"

class TestCSLEngineRefToCslJson:
    def test_basic_conversion(self, engine, sample_ref):
        from app.models import Reference, ReferenceType
        result = engine._reference_to_csl_json(sample_ref, index=1)
        assert result["id"] == "ref1"
        assert result["type"] == "book"
        assert result["title"] == "Deep Learning"
        assert len(result["author"]) == 2
        assert result["issued"]["date-parts"] == [[2016]]

    def test_missing_fields(self, engine):
        from app.models import Reference, ReferenceType
        ref = Reference(reference_id="r1", citation_key="k", raw_text="t", index=1)
        result = engine._reference_to_csl_json(ref, index=1)
        assert result["type"] == "article"
        assert "author" not in result
        assert "issued" not in result

class TestCSLEngineFormatFallback:
    def test_ieee_fallback(self, engine, sample_ref):
        from app.models import Reference, ReferenceType
        result = engine._format_ieee_fallback(sample_ref)
        assert "Goodfellow, Ian" in result
        assert "Deep Learning" in result
        assert "MIT Press" in result
        assert "10.1234/dl" in result

    def test_apa_fallback(self, engine, sample_ref):
        from app.models import Reference, ReferenceType
        result = engine._format_apa_fallback(sample_ref)
        assert "Goodfellow" in result
        assert "2016" in result
        assert "Deep Learning" in result

    def test_apa_single_author(self, engine):
        from app.models import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", title="A Book", authors=["Smith, J."],
            year=2020, citation_key="k", raw_text="t", index=1,
        )
        result = engine._format_apa_fallback(ref)
        assert "Smith" in result

    def test_apa_two_authors(self, engine):
        from app.models import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", title="A Book", authors=["Smith, J.", "Doe, A."],
            year=2020, citation_key="k", raw_text="t", index=1,
        )
        result = engine._format_apa_fallback(ref)
        assert "&" in result

    def test_apa_three_authors(self, engine):
        from app.models import Reference, ReferenceType
        ref = Reference(
            reference_id="r1", title="A Book",
            authors=["Smith, J.", "Doe, A.", "Lee, K."],
            year=2020, citation_key="k", raw_text="t", index=1,
        )
        result = engine._format_apa_fallback(ref)
        assert result.count(",") >= 2

    def test_format_references_empty(self, engine):
        from app.models import Reference, ReferenceType
        assert engine.format_references([]) == []

    def test_format_reference_single_ieee(self, engine, sample_ref):
        from app.models import Reference, ReferenceType
        result = engine.format_reference(sample_ref, style="ieee")
        assert "Deep Learning" in result

    def test_format_reference_single_apa(self, engine, sample_ref):
        from app.models import Reference, ReferenceType
        result = engine.format_reference(sample_ref, style="apa")
        assert "Deep Learning" in result

class TestCSLEngineApaAuthors:
    def test_no_authors(self, engine):
        from app.models import Reference, ReferenceType
        assert engine._format_apa_authors([]) == "Unknown Author"

    def test_one_author(self, engine):
        from app.models import Reference, ReferenceType
        assert engine._format_apa_authors(["Smith, J."]) == "Smith, J."

    def test_two_authors(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._format_apa_authors(["Smith, J.", "Doe, A."])
        assert "&" in result

    def test_three_authors(self, engine):
        from app.models import Reference, ReferenceType
        result = engine._format_apa_authors(["Smith, J.", "Doe, A.", "Lee, K."])
        assert result.endswith("& Lee, K.")
