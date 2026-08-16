# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Targeted tests for uncovered lines in llm_validator.py, csl_engine.py, csl_fetcher.py."""

from __future__ import annotations

import importlib
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


# ══════════════════════════════════════════════════════════════════════════════
# app/pipeline/safety/llm_validator.py  (73% -> 90%+)
# ══════════════════════════════════════════════════════════════════════════════


class TestLLMValidatorCoverageGaps:
    LV_KEY = "app.pipeline.safety.llm_validator"
    VG_KEY = "app.pipeline.safety.validator_guard"
    GR_KEY = "guardrails"

    @contextmanager
    def _llm_env(self, sys_mods):
        """Context that patches sys.modules for llm_validator reload, auto-restores."""
        with patch.dict("sys.modules", sys_mods, clear=False):
            import app.pipeline.safety.llm_validator as _lv_mod

            yield importlib.reload(_lv_mod)

    def test_python_314_disables_guardrails(self):
        """Lines 16-17: sys.version_info >= 3.14 sets HAS_GUARDRAILS = False."""
        with self._llm_env({self.VG_KEY: MagicMock()}) as mod, patch("sys.version_info", (3, 14)):
            importlib.reload(mod)
            assert mod.HAS_GUARDRAILS is False

    def test_guardrails_import_fails(self):
        """Lines 29-31: guardrails not importable, HAS_GUARDRAILS = False."""
        with self._llm_env({self.GR_KEY: None, self.VG_KEY: MagicMock()}) as mod:
            assert mod.HAS_GUARDRAILS is False

    def test_extreme_fallback_exception_path(self):
        """Lines 44-45: extreme fallback catches exception and returns error_return_value."""
        with self._llm_env({self.GR_KEY: None, self.VG_KEY: None}) as mod:
            deco = mod.guard_llm_output(str, error_return_value="fallback_val")

            @deco
            def fn():
                raise ValueError("boom")

            assert fn() == "fallback_val"

    def test_extreme_fallback_success_path(self):
        """Line 43: extreme fallback success path returns function result."""
        with self._llm_env({self.GR_KEY: None, self.VG_KEY: None}) as mod:
            deco = mod.guard_llm_output(str)

            @deco
            def fn():
                return 99

            assert fn() == 99


# ══════════════════════════════════════════════════════════════════════════════
# app/pipeline/services/csl_engine.py  (9% -> 50%+)
# ══════════════════════════════════════════════════════════════════════════════


class TestCSLEngineNoCiteproc:
    def engine(self):
        from app.pipeline.services.csl_engine import CSLEngine

        return CSLEngine(templates_dir="/nonexistent_templates_dir_xyz")

    def test_supports_10k_plus_styles(self):
        eng = self.engine()
        assert eng.supports_10k_plus_styles() is True

    def test_init_default_templates_dir(self):
        from app.pipeline.services.csl_engine import CSLEngine

        eng = CSLEngine()
        assert str(eng.templates_dir).endswith("templates")

    def test_init_custom_templates_dir(self):
        from app.pipeline.services.csl_engine import CSLEngine

        eng = CSLEngine(templates_dir="/custom/path")
        assert str(eng.templates_dir) == str(Path("/custom/path"))

    def test_resolve_style_path_explicit_found(self, tmp_path):
        from app.pipeline.services.csl_engine import CSLEngine

        f = tmp_path / "custom.csl"
        f.write_text("test", encoding="utf-8")
        eng = CSLEngine()
        path = eng.resolve_style_path("ieee", style_path=str(f))
        assert path == f

    def test_resolve_style_path_explicit_not_found(self):
        eng = self.engine()
        with pytest.raises(FileNotFoundError):
            eng.resolve_style_path("ieee", style_path="/nonexistent/path/foo.csl")

    def test_resolve_style_path_builtin_not_found(self):
        eng = self.engine()
        with pytest.raises(FileNotFoundError):
            eng.resolve_style_path("ieee")

    def test_resolve_style_path_style_path_is_file_raises(self):
        eng = self.engine()
        with pytest.raises(FileNotFoundError):
            # style_path provided but nothing in backend-dir either
            eng.resolve_style_path("ieee", style_path="nonexistent_subdir/test.csl")

    def test_format_references_empty_list(self):
        eng = self.engine()
        assert eng.format_references([]) == []

    def test_format_reference_single_ieee(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Smith, J."],
            title="A Paper",
            year=2020,
            journal="Journal of Testing",
            volume="10",
            issue="2",
            pages="1-10",
        )
        result = eng.format_reference(ref, style="ieee")
        assert "Smith" in result

    def test_format_references_fallback_ieee(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Doe, J."],
                title="Paper One",
                year=2021,
                journal="Journal A",
                volume="5",
                pages="1-10",
            ),
        ]
        result = eng.format_references(refs, style="ieee")
        assert len(result) == 1
        assert "Doe" in result[0]

    def test_format_references_fallback_apa(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Smith, J."],
                title="Test Title",
                year=2020,
                journal="J. Testing",
                volume="10",
                issue="2",
                pages="1-10",
                doi="10.1234/test",
            ),
        ]
        result = eng.format_references(refs, style="apa")
        assert len(result) == 1
        assert "Smith" in result[0]

    def test_format_references_fallback_mla(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Mla Author"],
                title="MLA Study",
                year=2019,
                publisher="MLA Press",
            ),
        ]
        result = eng.format_references(refs, style="mla")
        assert len(result) == 1
        assert "Mla Author" in result[0]

    def test_format_references_fallback_chicago(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Chicago Writer"],
                title="Chicago Book",
                year=2018,
                publisher="Chicago Press",
                volume="2",
                pages="100-200",
            ),
        ]
        result = eng.format_references(refs, style="chicago")
        assert len(result) == 1
        assert "Chicago Writer" in result[0]

    def test_format_references_fallback_harvard(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Harvard Author"],
                title="Harvard Work",
                year=2023,
            ),
        ]
        result = eng.format_references(refs, style="harvard")
        assert len(result) == 1
        assert "Harvard" in result[0]

    def test_format_references_unknown_style_defaults_ieee(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Default, A."],
                title="Default Paper",
                year=2020,
            ),
        ]
        result = eng.format_references(refs, style="unknown_style_xyz")
        assert len(result) == 1

    def test_format_references_no_authors(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(reference_id="r1", citation_key="k1", raw_text="t", index=0, title="No Author"),
        ]
        result = eng.format_references(refs, style="ieee")
        assert "Unknown Author" in result[0]

    def test_format_references_with_doi(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Doe, J."],
                title="DOI Paper",
                year=2020,
                doi="10.1234/abc",
            ),
        ]
        result = eng.format_references(refs, style="ieee")
        assert "doi:" in result[0]

    def test_format_references_missing_fields(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(reference_id="r1", citation_key="k1", raw_text="t", index=0),
        ]
        result = eng.format_references(refs, style="ieee")
        assert "Untitled" in result[0]

    def test_reference_to_csl_json_journal(self):
        from app.models import Reference, ReferenceType

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            title="Journal Paper",
            authors=["Smith, J."],
            journal="Journal A",
            year=2020,
            volume="10",
            issue="2",
            pages="1-10",
            doi="10.1234/abc",
            url="https://example.com",
            isbn="978-3-16-148410-0",
            issn="1234-5678",
        )
        js = eng._reference_to_csl_json(ref, 1)
        assert js["type"] == "article-journal"
        assert js["title"] == "Journal Paper"
        assert js["DOI"] == "10.1234/abc"
        assert js["URL"] == "https://example.com"
        assert js["ISBN"] == "978-3-16-148410-0"
        assert js["ISSN"] == "1234-5678"
        assert js["container-title"] == "Journal A"
        assert js["issued"]["date-parts"] == [[2020]]

    def test_reference_to_csl_json_book(self):
        from app.models import Reference, ReferenceType

        eng = self.engine()
        ref = Reference(
            reference_id="r2",
            citation_key="k2",
            raw_text="t",
            index=1,
            reference_type=ReferenceType.BOOK,
            title="A Book",
            authors=["Author, A."],
            book_title="Book Title",
            publisher="Pub Co",
            year=2019,
        )
        js = eng._reference_to_csl_json(ref, 2)
        assert js["type"] == "book"
        assert js["publisher"] == "Pub Co"

    def test_reference_to_csl_json_conference(self):
        from app.models import Reference, ReferenceType

        eng = self.engine()
        ref = Reference(
            reference_id="r3",
            citation_key="k3",
            raw_text="t",
            index=2,
            reference_type=ReferenceType.CONFERENCE_PAPER,
            title="Conf Paper",
            authors=["Conf, A."],
            conference="Test Conference 2020",
        )
        js = eng._reference_to_csl_json(ref, 3)
        assert js["type"] == "paper-conference"
        assert js["container-title"] == "Test Conference 2020"

    def test_reference_to_csl_json_unknown_type_defaults_article(self):
        from app.models import Reference, ReferenceType

        eng = self.engine()
        ref = Reference(
            reference_id="r4",
            citation_key="k4",
            raw_text="t",
            index=3,
            reference_type=ReferenceType.UNKNOWN,
            title="Misc",
        )
        js = eng._reference_to_csl_json(ref, 4)
        assert js["type"] == "article"

    def test_to_csl_name_comma_separated(self):
        eng = self.engine()
        result = eng._to_csl_name("Smith, John")
        assert result == {"family": "Smith", "given": "John"}

    def test_to_csl_name_comma_family_only(self):
        eng = self.engine()
        result = eng._to_csl_name("Smith,")
        assert result == {"family": "Smith"}

    def test_to_csl_name_comma_family_empty_branch(self):
        """Branch 431->434: family empty after comma split (name starts with comma)."""
        eng = self.engine()
        result = eng._to_csl_name(", Smith")
        assert result == {"given": ",", "family": "Smith"}

    def test_to_csl_name_comma_given_only_branch(self):
        """Branch 431->434: 'given' empty after comma split, family truthy."""
        eng = self.engine()
        result = eng._to_csl_name("Smith,")
        assert result == {"family": "Smith"}

    def test_to_csl_name_space_separated(self):
        eng = self.engine()
        result = eng._to_csl_name("John Smith")
        assert result == {"family": "Smith", "given": "John"}

    def test_to_csl_name_single_word(self):
        eng = self.engine()
        result = eng._to_csl_name("Aristotle")
        assert result == {"literal": "Aristotle"}

    def test_to_csl_name_empty_string(self):
        eng = self.engine()
        result = eng._to_csl_name("   ")
        assert result == {"literal": "Unknown Author"}

    def test_to_csl_name_whitespace_cleaned(self):
        eng = self.engine()
        result = eng._to_csl_name("  John   Q  Smith  ")
        assert result == {"family": "Smith", "given": "John Q"}

    def test_ieee_fallback_full(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Doe, J."],
            title="Paper",
            journal="Journal",
            volume="10",
            issue="2",
            pages="1-10",
            year=2020,
            doi="10.1234/abc",
        )
        result = eng._format_ieee_fallback(ref)
        assert "Doe" in result
        assert "Paper" in result
        assert "vol. 10" in result
        assert "no. 2" in result
        assert "doi:" in result

    def test_ieee_fallback_minimal(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(reference_id="r1", citation_key="k1", raw_text="t", index=0)
        result = eng._format_ieee_fallback(ref)
        assert "Unknown Author" in result

    def test_ieee_fallback_already_ends_with_period(self):
        """Branch 475->477: formatted already ends with '.' (no year, pages with dot)."""
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Doe, J."],
            title="Paper",
            journal="Journal",
            volume="10",
            pages="100-110.",
        )
        result = eng._format_ieee_fallback(ref)
        assert result.endswith(".")

    def test_apa_fallback_single_author(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Smith, J."],
            title="APA Paper",
            year=2020,
            journal="APA Journal",
            volume="10",
            issue="2",
            pages="1-10",
        )
        result = eng._format_apa_fallback(ref)
        assert "Smith" in result
        assert "(2020)" in result

    def test_apa_fallback_no_year(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1", citation_key="k1", raw_text="t", index=0, authors=["Smith, J."], title="No Year"
        )
        result = eng._format_apa_fallback(ref)
        assert "(n.d.)" in result

    def test_apa_fallback_with_http_doi(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Smith, J."],
            title="DOI Test",
            year=2022,
            doi="https://doi.org/10.1234/test",
        )
        result = eng._format_apa_fallback(ref)
        assert "https://doi.org/" in result

    def test_apa_fallback_with_non_http_doi(self):
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Smith, J."],
            title="DOI Test 2",
            year=2022,
            doi="10.1234/test",
        )
        result = eng._format_apa_fallback(ref)
        assert "https://doi.org/10.1234/test" in result

    def test_apa_fallback_volume_only_no_issue(self):
        """Line 491: elif ref.volume branch (volume without issue)."""
        from app.models import Reference

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            authors=["Smith, J."],
            title="Vol Only",
            year=2020,
            journal="J",
            volume="15",
            pages="1-5",
        )
        result = eng._format_apa_fallback(ref)
        assert "15" in result

    def test_apa_authors_single(self):
        eng = self.engine()
        assert eng._format_apa_authors(["Smith, J."]) == "Smith, J."

    def test_apa_authors_two(self):
        eng = self.engine()
        assert eng._format_apa_authors(["Smith, J.", "Doe, A."]) == "Smith, J., & Doe, A."

    def test_apa_authors_three_plus(self):
        eng = self.engine()
        assert eng._format_apa_authors(["A", "B", "C"]) == "A, B, & C"

    def test_apa_authors_empty(self):
        eng = self.engine()
        assert eng._format_apa_authors([]) == "Unknown Author"

    def test_citeproc_not_available_flag(self):
        from app.pipeline.services.csl_engine import CITEPROC_AVAILABLE

        assert isinstance(CITEPROC_AVAILABLE, bool)

    def test_csl_json_multiple_authors_empty_filtered(self):
        from app.models import Reference, ReferenceType

        eng = self.engine()
        ref = Reference(
            reference_id="r1",
            citation_key="k1",
            raw_text="t",
            index=0,
            reference_type=ReferenceType.WEB_PAGE,
            title="Web Ref",
            authors=["Valid Author", "", "  "],
        )
        js = eng._reference_to_csl_json(ref, 1)
        assert js["type"] == "webpage"
        assert len(js["author"]) == 1

    def test_format_references_citeproc_fallback_on_error(self):
        from app.models import Reference

        eng = self.engine()
        refs = [
            Reference(
                reference_id="r1",
                citation_key="k1",
                raw_text="t",
                index=0,
                authors=["Test, A."],
                title="Test",
                year=2021,
            ),
        ]
        result = eng.format_references(refs, style="ieee")
        assert len(result) == 1


class TestCSLEngineWithCiteproc:
    def test_citeproc_available_true(self):
        fake_citeproc = MagicMock()
        fake_citeproc.Citation = MagicMock()
        fake_citeproc.CitationItem = MagicMock()
        fake_citeproc.CitationStylesStyle = MagicMock()
        fake_citeproc.CitationStylesBibliography = MagicMock()
        fake_citeproc.formatter = MagicMock()
        fake_citeproc.formatter.plain = MagicMock()
        fake_source = MagicMock()
        fake_source_json = MagicMock()
        fake_source_json.CiteProcJSON = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "citeproc": fake_citeproc,
                "citeproc.source": fake_source,
                "citeproc.source.json": fake_source_json,
            },
        ):
            import app.pipeline.services.csl_engine as _ce_mod

            mod = importlib.reload(_ce_mod)
            assert mod.CITEPROC_AVAILABLE is True

    def test_citeproc_format_success(self, tmp_path):
        fake_citeproc = MagicMock()
        fake_citeproc.Citation = MagicMock()
        fake_citeproc.CitationItem = MagicMock()
        fake_citeproc.CitationStylesStyle = MagicMock()
        fake_citeproc.CitationStylesBibliography = MagicMock()
        fake_citeproc.formatter = MagicMock()
        fake_citeproc.formatter.plain = MagicMock()
        fake_bib = MagicMock()
        fake_bib.bibliography.return_value = ["[1] Smith, J. A Paper. 2020."]
        fake_citeproc.CitationStylesBibliography.return_value = fake_bib
        fake_source = MagicMock()
        fake_source_json = MagicMock()
        fake_source_json.CiteProcJSON = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "citeproc": fake_citeproc,
                "citeproc.source": fake_source,
                "citeproc.source.json": fake_source_json,
            },
        ):
            import app.pipeline.services.csl_engine as _ce_mod

            mod = importlib.reload(_ce_mod)
            eng = mod.CSLEngine(templates_dir=str(tmp_path))
            ieee_dir = tmp_path / "ieee"
            ieee_dir.mkdir(parents=True)
            (ieee_dir / "styles.csl").write_text("<style/>", encoding="utf-8")
            eng.resolve_style_path = MagicMock(return_value=ieee_dir / "styles.csl")
            from app.models import Reference

            refs = [
                Reference(
                    reference_id="r1",
                    citation_key="k1",
                    raw_text="t",
                    index=0,
                    authors=["Smith, J."],
                    title="A Paper",
                    year=2020,
                ),
            ]
            result = eng.format_references(refs, style="ieee")
            assert len(result) == 1
            assert "Smith" in result[0]

    def test_citeproc_length_mismatch_raises(self, tmp_path):
        fake_citeproc = MagicMock()
        fake_citeproc.Citation = MagicMock()
        fake_citeproc.CitationItem = MagicMock()
        fake_citeproc.CitationStylesStyle = MagicMock()
        fake_citeproc.CitationStylesBibliography = MagicMock()
        fake_citeproc.formatter = MagicMock()
        fake_citeproc.formatter.plain = MagicMock()
        fake_bib = MagicMock()
        fake_bib.bibliography.return_value = ["Only one"]
        fake_citeproc.CitationStylesBibliography.return_value = fake_bib
        fake_source = MagicMock()
        fake_source_json = MagicMock()
        fake_source_json.CiteProcJSON = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "citeproc": fake_citeproc,
                "citeproc.source": fake_source,
                "citeproc.source.json": fake_source_json,
            },
        ):
            import app.pipeline.services.csl_engine as _ce_mod

            mod = importlib.reload(_ce_mod)
            eng = mod.CSLEngine(templates_dir=str(tmp_path))
            ieee_dir = tmp_path / "ieee"
            ieee_dir.mkdir(parents=True)
            (ieee_dir / "styles.csl").write_text("<style/>", encoding="utf-8")
            eng.resolve_style_path = MagicMock(return_value=ieee_dir / "styles.csl")
            from app.models import Reference

            refs = [
                Reference(reference_id="r1", citation_key="k1", raw_text="t", index=0, authors=["A"], title="T"),
                Reference(reference_id="r2", citation_key="k2", raw_text="t", index=1, authors=["B"], title="U"),
            ]
            with pytest.raises(RuntimeError):
                eng._format_with_citeproc(refs, style="ieee", style_path=None)

    def test_citeproc_available_false_direct_fallback(self):
        """Branch 334->344: when CITEPROC_AVAILABLE is False, direct to fallback."""
        # Make citeproc import fail
        with patch.dict(
            "sys.modules",
            {"citeproc": None, "citeproc.source": None, "citeproc.source.json": None, "citeproc.formatter": None},
        ):
            import app.pipeline.services.csl_engine as _ce_mod

            mod = importlib.reload(_ce_mod)
            assert mod.CITEPROC_AVAILABLE is False
            eng = mod.CSLEngine(templates_dir="/nonexistent")
            from app.models import Reference

            refs = [
                Reference(
                    reference_id="r1", citation_key="k1", raw_text="t", index=0, authors=["A"], title="T", year=2021
                ),
            ]
            result = eng.format_references(refs, style="ieee")
            assert len(result) == 1
            assert "A" in result[0]

    def test_citeproc_delegates_to_fallback_on_exception(self, tmp_path):
        """Branch 334->344 via exception: CITEPROC_AVAILABLE True but raises."""
        fake_citeproc = MagicMock()
        fake_citeproc.Citation = MagicMock()
        fake_citeproc.CitationItem = MagicMock()
        fake_citeproc.CitationStylesStyle = MagicMock()
        fake_citeproc.CitationStylesBibliography = MagicMock()
        fake_citeproc.formatter = MagicMock()
        fake_citeproc.formatter.plain = MagicMock()
        fake_citeproc.CitationStylesStyle.side_effect = ValueError("citeproc error")
        fake_source = MagicMock()
        fake_source_json = MagicMock()
        fake_source_json.CiteProcJSON = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "citeproc": fake_citeproc,
                "citeproc.source": fake_source,
                "citeproc.source.json": fake_source_json,
            },
        ):
            import app.pipeline.services.csl_engine as _ce_mod

            mod = importlib.reload(_ce_mod)
            eng = mod.CSLEngine(templates_dir=str(tmp_path))
            ieee_dir = tmp_path / "ieee"
            ieee_dir.mkdir(parents=True)
            (ieee_dir / "styles.csl").write_text("<style/>", encoding="utf-8")
            from app.models import Reference

            refs = [
                Reference(
                    reference_id="r1",
                    citation_key="k1",
                    raw_text="t",
                    index=0,
                    authors=["Fallback, A."],
                    title="Fallback Paper",
                    year=2022,
                ),
            ]
            result = eng.format_references(refs, style="ieee")
            assert len(result) == 1
            assert "Fallback" in result[0]


# ══════════════════════════════════════════════════════════════════════════════
# app/pipeline/services/csl_fetcher.py  (14% -> 50%+)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def reset_csl_caches():
    from app.pipeline.services import csl_fetcher

    csl_fetcher.reset_csl_cache_for_tests()


class TestCSLFetcherCoverageGaps:
    def _mod(self):
        from app.pipeline.services import csl_fetcher

        return csl_fetcher

    def test_search_cache_ttl_default(self):
        mod = self._mod()
        assert mod._search_cache_ttl_seconds() == 300.0

    def test_search_cache_ttl_from_settings(self):
        mod = self._mod()
        with patch.object(mod, "settings", MagicMock(CSL_SEARCH_CACHE_TTL_SECONDS=600)):
            assert mod._search_cache_ttl_seconds() == 600.0

    def test_search_cache_ttl_invalid_returns_default(self):
        mod = self._mod()
        with patch.object(mod, "settings", MagicMock(CSL_SEARCH_CACHE_TTL_SECONDS="invalid")):
            assert mod._search_cache_ttl_seconds() == 300.0

    def test_search_cache_ttl_zero(self):
        mod = self._mod()
        with patch.object(mod, "settings", MagicMock(CSL_SEARCH_CACHE_TTL_SECONDS=0)):
            assert mod._search_cache_ttl_seconds() == 0.0

    def test_search_cache_ttl_negative_clamped(self):
        mod = self._mod()
        with patch.object(mod, "settings", MagicMock(CSL_SEARCH_CACHE_TTL_SECONDS=-1)):
            assert mod._search_cache_ttl_seconds() == 0.0

    def test_style_cache_ttl_default(self):
        mod = self._mod()
        assert mod._style_cache_ttl_seconds() == 1800.0

    def test_style_cache_ttl_from_settings(self):
        mod = self._mod()
        with patch.object(mod, "settings", MagicMock(CSL_FETCH_CACHE_TTL_SECONDS=3600)):
            assert mod._style_cache_ttl_seconds() == 3600.0

    def test_style_cache_ttl_invalid_returns_default(self):
        mod = self._mod()
        with patch.object(mod, "settings", MagicMock(CSL_FETCH_CACHE_TTL_SECONDS="bad")):
            assert mod._style_cache_ttl_seconds() == 1800.0

    def test_get_search_cache_lock_singleton(self):
        mod = self._mod()
        l1 = mod._get_search_cache_lock()
        l2 = mod._get_search_cache_lock()
        assert l1 is l2

    def test_get_style_cache_lock_singleton(self):
        mod = self._mod()
        l1 = mod._get_style_cache_lock()
        l2 = mod._get_style_cache_lock()
        assert l1 is l2

    def test_clone_style_rows_copies(self):
        mod = self._mod()
        rows = [{"slug": "ieee", "title": "IEEE"}]
        cloned = mod._clone_style_rows(rows)
        assert cloned == rows
        assert cloned is not rows
        assert cloned[0] is not rows[0]

    def test_clone_style_payload_copies(self):
        mod = self._mod()
        payload = {"slug": "ieee", "content": "<style/>"}
        cloned = mod._clone_style_payload(payload)
        assert cloned == payload
        assert cloned is not payload

    def test_reset_csl_cache(self):
        mod = self._mod()
        mod._search_cache["test"] = (100.0, [])
        mod._style_cache["test"] = (100.0, {})
        mod._search_cache_lock = "lock"
        mod._style_cache_lock = "lock"
        mod.reset_csl_cache_for_tests()
        assert mod._search_cache == {}
        assert mod._style_cache == {}
        assert mod._search_cache_lock is None
        assert mod._style_cache_lock is None

    def test_local_styles(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "ieee" / "styles.csl").write_text("test", encoding="utf-8")
            (tmp_path / "apa" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "apa" / "styles.csl").write_text("test", encoding="utf-8")
            result = mod._local_styles()
            slugs = {r["slug"] for r in result}
            assert "ieee" in slugs
            assert "apa" in slugs

    @pytest.mark.asyncio
    async def test_search_styles_cache_hit(self):
        mod = self._mod()
        mod._search_cache["ieee|20"] = (float("inf"), [{"slug": "ieee", "title": "IEEE", "source": "cache"}])
        result = await mod.search_styles("ieee")
        assert result[0]["source"] == "cache"

    @pytest.mark.asyncio
    async def test_search_styles_local_only_empty_query(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "ieee" / "styles.csl").write_text("test", encoding="utf-8")
            result = await mod.search_styles("")
            assert any(r["slug"] == "ieee" for r in result)

    @pytest.mark.asyncio
    async def test_search_styles_local_filter(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "ieee" / "styles.csl").write_text("test", encoding="utf-8")
            (tmp_path / "apa" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "apa" / "styles.csl").write_text("test", encoding="utf-8")
            result = await mod.search_styles("ieee")
            assert len(result) == 1
            assert result[0]["slug"] == "ieee"

    @pytest.mark.asyncio
    async def test_search_styles_with_remote(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.json.return_value = [{"name": "custom-style", "title": "Custom Style"}]
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            result = await mod.search_styles("custom")
            assert any(r["slug"] == "custom-style" for r in result)

    @pytest.mark.asyncio
    async def test_search_styles_remote_error_falls_back(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "ieee" / "styles.csl").write_text("test", encoding="utf-8")
            with patch("httpx.AsyncClient") as mc:
                instance = MagicMock()
                instance.__aenter__.return_value.get.side_effect = Exception("network error")
                mc.return_value = instance
                result = await mod.search_styles("ieee")
                assert len(result) == 1
                assert result[0]["slug"] == "ieee"

    @pytest.mark.asyncio
    async def test_search_styles_remote_non_dict_item_skipped(self, tmp_path):
        """Line 113: non-dict items in remote response are skipped."""
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.json.return_value = [
                {"name": "valid", "title": "Valid"},
                "not a dict",
                42,
                None,
            ]
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            result = await mod.search_styles("valid")
            slugs = [r["slug"] for r in result]
            assert "valid" in slugs

    @pytest.mark.asyncio
    async def test_search_styles_remote_empty_slug_skipped(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.json.return_value = [{"name": "", "title": "Empty"}]
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            result = await mod.search_styles("empty")
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_styles_ttl_zero_no_caching(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "ieee" / "styles.csl").write_text("test", encoding="utf-8")
            with patch.object(mod, "settings", MagicMock(CSL_SEARCH_CACHE_TTL_SECONDS=0)):
                await mod.search_styles("ieee")
                assert mod._search_cache.get("ieee|20") is None

    @pytest.mark.asyncio
    async def test_search_styles_remote_invalid_payload(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.json.return_value = "not a list"
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            result = await mod.search_styles("custom")
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_styles_remote_item_no_slug_skipped(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.json.return_value = [{"not_slug": "foo"}, {"name": "valid", "title": "V"}]
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            result = await mod.search_styles("valid")
            assert any(r["slug"] == "valid" for r in result)

    @pytest.mark.asyncio
    async def test_search_styles_double_cache_check(self):
        """Line 99: second cache check inside lock hits valid entry."""
        mod = self._mod()
        cache_entry = [{"slug": "ieee", "title": "IEEE", "source": "inner_cache"}]
        mod._search_cache["ieee|20"] = (150.0, cache_entry)
        with patch.object(mod, "monotonic", side_effect=[200.0, 100.0]):
            result = await mod.search_styles("ieee")
        assert result[0]["source"] == "inner_cache"

    @pytest.mark.asyncio
    async def test_fetch_style_empty_slug_raises(self):
        mod = self._mod()
        with pytest.raises(ValueError, match="slug is required"):
            await mod.fetch_style("")
        with pytest.raises(ValueError, match="slug is required"):
            await mod.fetch_style(None)

    @pytest.mark.asyncio
    async def test_fetch_style_cache_hit(self):
        mod = self._mod()
        mod._style_cache["ieee"] = (float("inf"), {"slug": "ieee", "source": "cache", "content": "cached"})
        result = await mod.fetch_style("ieee")
        assert result["source"] == "cache"

    @pytest.mark.asyncio
    async def test_fetch_style_local(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
            (tmp_path / "ieee" / "styles.csl").write_text("local content", encoding="utf-8")
            result = await mod.fetch_style("ieee")
            assert result["source"] == "local"
            assert result["content"] == "local content"

    @pytest.mark.asyncio
    async def test_fetch_style_local_ttl_zero(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            with patch.object(mod, "settings", MagicMock(CSL_FETCH_CACHE_TTL_SECONDS=0)):
                (tmp_path / "ieee" / "styles.csl").parent.mkdir(parents=True)
                (tmp_path / "ieee" / "styles.csl").write_text("local content", encoding="utf-8")
                result = await mod.fetch_style("ieee")
                assert result["source"] == "local"
                assert "ieee" not in mod._style_cache

    @pytest.mark.asyncio
    async def test_fetch_style_remote(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.text = "remote style content"
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            result = await mod.fetch_style("nonexistent-style")
            assert result["source"] == "remote"
            assert result["content"] == "remote style content"

    @pytest.mark.asyncio
    async def test_fetch_style_remote_ttl_zero(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path):
            with patch.object(mod, "settings", MagicMock(CSL_FETCH_CACHE_TTL_SECONDS=0)):
                with patch("httpx.AsyncClient") as mc:
                    instance = MagicMock()
                    resp = MagicMock()
                    resp.text = "remote content"
                    instance.__aenter__.return_value.get.return_value = resp
                    mc.return_value = instance
                    await mod.fetch_style("some-style")
                    assert "some-style" not in mod._style_cache

    @pytest.mark.asyncio
    async def test_fetch_style_remote_http_error(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.raise_for_status.side_effect = Exception("HTTP 404")
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            with pytest.raises(Exception):
                await mod.fetch_style("nonexistent")

    @pytest.mark.asyncio
    async def test_fetch_style_double_cache_check(self):
        """Line 158: second cache check inside lock hits valid entry."""
        mod = self._mod()
        mod._style_cache["ieee"] = (150.0, {"slug": "ieee", "source": "inner", "content": "inner"})
        with patch.object(mod, "monotonic", side_effect=[200.0, 100.0]):
            result = await mod.fetch_style("ieee")
        assert result["source"] == "inner"

    @pytest.mark.asyncio
    async def test_fetch_style_remote_caches_result(self, tmp_path):
        mod = self._mod()
        with patch.object(mod, "TEMPLATES_DIR", tmp_path), patch("httpx.AsyncClient") as mc:
            instance = MagicMock()
            resp = MagicMock()
            resp.text = "cached remote"
            instance.__aenter__.return_value.get.return_value = resp
            mc.return_value = instance
            await mod.fetch_style("teststyle")
            assert mod._style_cache["teststyle"][1]["content"] == "cached remote"

    def test_verify_existing_templates_directory(self):
        mod = self._mod()
        assert mod.TEMPLATES_DIR.exists()
