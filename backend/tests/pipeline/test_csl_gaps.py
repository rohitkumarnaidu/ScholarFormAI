# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models import Reference


def _ref(**kw) -> Reference:
    from app.models import Reference

    defaults = dict(reference_id="r1", citation_key="k", raw_text="t", index=1)
    defaults.update(kw)
    return Reference(**defaults)


# =============================================================================
# csl_engine.py gaps
# =============================================================================


class TestCslEngineGaps:
    def _engine(self):
        from app.pipeline.services.csl_engine import CSLEngine

        return CSLEngine(templates_dir=str(Path(__file__).resolve().parent))

    def test_resolve_path_exists(self, tmp_path):
        from app.pipeline.services.csl_engine import CSLEngine

        f = tmp_path / "s.csl"
        f.write_text("")
        e = CSLEngine(templates_dir=str(tmp_path))
        assert e.resolve_style_path("ieee", style_path=str(f)) == f

    def test_resolve_path_not_found_raises(self, tmp_path):
        from app.pipeline.services.csl_engine import CSLEngine

        e = CSLEngine(templates_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="CSL style file not found"):
            e.resolve_style_path("ieee", style_path=str(tmp_path / "nope.csl"))

    def test_citeproc_fallback(self):
        e = self._engine()
        ref = _ref(authors=["Doe"], title="T", journal="J", year=2024)
        with patch.object(e, "_format_with_citeproc", side_effect=ValueError("down")):
            with patch("app.pipeline.services.csl_engine.CITEPROC_AVAILABLE", True):
                r = e.format_references([ref], style="ieee")
        assert len(r) == 1
        assert "Doe" in r[0]

    def test_length_mismatch_raises(self):
        e = self._engine()
        ref = _ref(authors=["Doe"], title="T", journal="J", year=2024)
        with patch.object(e, "resolve_style_path", return_value=Path("d.csl")):
            with patch("app.pipeline.services.csl_engine.CiteProcJSON"):
                with patch("app.pipeline.services.csl_engine.CitationStylesStyle"):
                    with patch("app.pipeline.services.csl_engine.CitationStylesBibliography") as csb:
                        csb.return_value = MagicMock(bibliography=lambda: ["one"])
                        with patch("app.pipeline.services.csl_engine.Citation"):
                            with patch("app.pipeline.services.csl_engine.CitationItem"):
                                with pytest.raises(RuntimeError, match="output length mismatch"):
                                    e._format_with_citeproc([ref, ref], "ieee", None)

    def test_ieee_fallback_no_venue(self):
        from app.pipeline.services.csl_engine import CSLEngine

        e = CSLEngine()
        r = e._format_ieee_fallback(_ref(authors=["Doe"], title="T", year=2024))
        assert "2024" in r

    def test_ieee_fallback_vol_issue_pages_doi(self):
        from app.pipeline.services.csl_engine import CSLEngine

        e = CSLEngine()
        r = e._format_ieee_fallback(
            _ref(
                authors=["Doe"], title="T", journal="J", volume="5", issue="3", pages="10-20", year=2024, doi="10.1/abc"
            )
        )
        assert all(x in r for x in ["vol. 5", "no. 3", "pp. 10-20", "doi"])

    def test_apa_fallback_vol_issue(self):
        from app.pipeline.services.csl_engine import CSLEngine

        e = CSLEngine()
        r = e._format_apa_fallback(_ref(authors=["Doe"], title="T", journal="J", volume="5", issue="3", year=2024))
        assert "5(3)" in r

    def test_apa_fallback_doi_http(self):
        from app.pipeline.services.csl_engine import CSLEngine

        e = CSLEngine()
        r = e._format_apa_fallback(_ref(authors=["Doe"], title="T", year=2024, doi="https://doi.org/10.1/abc"))
        assert "https://doi.org/10.1/abc" in r

    def test_csl_json_all_fields(self):
        from app.pipeline.services.csl_engine import CSLEngine

        e = CSLEngine()
        ref = _ref(
            authors=["Doe"],
            title="T",
            journal="J",
            year=2024,
            volume="5",
            issue="3",
            pages="10-20",
            doi="10.1",
            url="https://e.com",
            isbn="978-1",
            issn="1234-5678",
        )
        csl = e._reference_to_csl_json(ref, 1)
        for k in ["volume", "issue", "URL", "ISBN", "ISSN", "DOI"]:
            assert k in csl

    def test_to_csl_name_comma_no_given(self):
        from app.pipeline.services.csl_engine import CSLEngine

        assert CSLEngine()._to_csl_name("Doe,") == {"family": "Doe"}

    def test_format_fallback_apa(self):
        from app.pipeline.services.csl_engine import CSLEngine

        r = CSLEngine()._format_fallback(_ref(authors=["Doe"], title="T", year=2024), style="apa")
        assert "(2024)" in r

    def test_apa_authors_three(self):
        from app.pipeline.services.csl_engine import CSLEngine

        r = CSLEngine()._format_apa_authors(["A", "B", "C"])
        assert " & C" in r


# =============================================================================
# csl_fetcher.py gaps
# =============================================================================


class TestCslFetcherGaps:
    @pytest.fixture(autouse=True)
    def _reset(self):
        import app.pipeline.services.csl_fetcher as cf

        cf._search_cache = {}
        cf._style_cache = {}
        cf._search_cache_lock = None
        cf._style_cache_lock = None

    @pytest.mark.asyncio
    async def test_ttl_bad_string(self):
        from app.pipeline.services.csl_fetcher import _search_cache_ttl_seconds

        with patch("app.pipeline.services.csl_fetcher.settings") as ms:
            ms.CSL_SEARCH_CACHE_TTL_SECONDS = "bad"
            assert _search_cache_ttl_seconds() == 300.0

    @pytest.mark.asyncio
    async def test_style_ttl_bad_string(self):
        from app.pipeline.services.csl_fetcher import _style_cache_ttl_seconds

        with patch("app.pipeline.services.csl_fetcher.settings") as ms:
            ms.CSL_FETCH_CACHE_TTL_SECONDS = None
            assert _style_cache_ttl_seconds() == 1800.0

    @pytest.mark.asyncio
    async def test_lock_reused(self):
        from app.pipeline.services.csl_fetcher import _get_search_cache_lock, _get_style_cache_lock

        assert _get_search_cache_lock() is _get_search_cache_lock()
        assert _get_style_cache_lock() is _get_style_cache_lock()
