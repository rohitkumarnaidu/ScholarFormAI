# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from unittest.mock import patch, MagicMock
from app.pipeline.parsing.parser_factory import ParserFactory


@pytest.fixture
def factory():
    with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
        mock_s.ENABLE_NOUGAT_PARSER = False
        yield ParserFactory()


class TestParserFactoryInit:
    def test_init_registers_default_parsers(self, factory):
        assert len(factory.parsers) >= 2
        types = {p.__class__.__name__ for p in factory.parsers}
        assert "DocxParser" in types
        assert "PdfParser" in types

    def test_init_skips_failed_parsers(self):
        with patch("app.pipeline.parsing.parser_factory.DocxParser", side_effect=Exception("fail")):
            with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
                mock_s.ENABLE_NOUGAT_PARSER = False
                f = ParserFactory()
                assert all(not isinstance(p, MagicMock) for p in f.parsers)

    def test_init_enables_nougat_when_configured(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = True
            with patch("app.pipeline.parsing.nougat_parser.NougatParser") as mock_n:
                mock_n.return_value = MagicMock()
                f = ParserFactory()
                assert mock_n.called

    def test_init_nougat_import_error(self):
        with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
            mock_s.ENABLE_NOUGAT_PARSER = True
            with patch("builtins.__import__", side_effect=ImportError("no nougat")):
                f = ParserFactory()
                names = {p.__class__.__name__ for p in f.parsers}
                assert "NougatParser" not in names

    def test_init_with_pytest_env(self):
        with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": "test_something.py::test_func"}):
            with patch("app.pipeline.parsing.parser_factory.settings") as mock_s:
                mock_s.ENABLE_NOUGAT_PARSER = False
                f = ParserFactory()
                assert len(f.parsers) >= 2


class TestParserFactoryGetParser:
    def test_get_parser_docx(self, factory):
        parser = factory.get_parser("/path/file.docx")
        assert parser.__class__.__name__ == "DocxParser"

    def test_get_parser_pdf(self, factory):
        parser = factory.get_parser("/path/file.pdf")
        assert parser.__class__.__name__ == "PdfParser"

    def test_get_parser_txt(self, factory):
        parser = factory.get_parser("/path/file.txt")
        assert parser.__class__.__name__ == "TxtParser"

    def test_get_parser_html(self, factory):
        parser = factory.get_parser("/path/file.html")
        assert parser.__class__.__name__ == "HtmlParser"

    def test_get_parser_md(self, factory):
        parser = factory.get_parser("/path/file.md")
        assert parser.__class__.__name__ == "MarkdownParser"

    def test_get_parser_tex(self, factory):
        parser = factory.get_parser("/path/file.tex")
        assert parser.__class__.__name__ == "TexParser"

    def test_get_parser_unknown_returns_none(self, factory):
        result = factory.get_parser("/path/file.xyz")
        assert result is None

    def test_get_parser_case_insensitive(self, factory):
        parser = factory.get_parser("/path/file.PDF")
        assert parser is not None


class TestParserFactorySupportedFormats:
    def test_get_supported_formats(self, factory):
        fmts = factory.get_supported_formats()
        assert ".docx" in fmts
        assert ".pdf" in fmts
        assert ".txt" in fmts
        assert ".html" in fmts
        assert ".md" in fmts
        assert ".tex" in fmts
        assert all(f.startswith(".") for f in fmts)
