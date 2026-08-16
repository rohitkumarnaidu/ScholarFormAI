# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock


class TestJATSGenerator:
    def _make_doc(self, metadata=None, blocks=None, equations=None, references=None):
        doc = MagicMock()
        doc.metadata = metadata or MagicMock()
        doc.metadata.title = "Test Title"
        doc.metadata.authors = ["John Doe"]
        doc.metadata.publication_date = datetime(2024, 6, 15)
        doc.metadata.volume = "10"
        doc.metadata.issue = "2"
        doc.metadata.abstract = "Test abstract"
        doc.metadata.keywords = ["AI", "ML"]
        doc.blocks = blocks or []
        doc.equations = equations or []
        doc.references = references or []
        return doc

    def _make_block(self, text="Body text", semantic_intent="body"):
        b = MagicMock()
        b.text = text
        b.metadata = {"semantic_intent": semantic_intent}
        return b

    def test_to_xml_basic(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        doc = self._make_doc()
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert xml.startswith("<!DOCTYPE article")
        assert "<article" in xml
        assert "Test Title" in xml
        assert "John" in xml
        assert "Doe" in xml
        assert "2024" in xml
        assert "Test abstract" in xml

    def test_no_authors_adds_placeholder(self):
        from lxml import etree

        from app.pipeline.export.jats_generator import JATSGenerator

        doc = self._make_doc()
        doc.metadata.authors = []
        gen = JATSGenerator()
        mock_parent = etree.Element("mock")
        gen._add_metadata(mock_parent, doc)
        xml = etree.tostring(mock_parent, encoding="unicode")
        assert "Author" in xml

    def test_no_abstract_skips(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        doc = self._make_doc()
        doc.metadata.abstract = None
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "<abstract>" not in xml

    def test_string_publication_date(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        doc = self._make_doc()
        doc.metadata.publication_date = "2024-06-15"
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "<year>2024" in xml

    def test_references_added(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.raw_text = "A reference text"
        ref.metadata = {"doi": "10.1234/test"}
        doc = self._make_doc(references=[ref])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "<ref-list>" in xml
        assert "10.1234/test" in xml

    def test_no_references_skipped(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        doc = self._make_doc(references=[])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "<ref-list>" not in xml

    def test_heading_and_body_blocks(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        heading = self._make_block(text="Introduction", semantic_intent="heading")
        body = self._make_block(text="This is the intro body.", semantic_intent="body")
        doc = self._make_doc(blocks=[heading, body])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "<sec>" in xml
        assert "<title>Introduction</title>" in xml
        assert "intro body" in xml

    def test_inline_equation(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        eq = MagicMock()
        eq.mathml = "<math><mi>x</mi></math>"
        eq.is_block = False
        eq.equation_id = "eq1"
        doc = self._make_doc(equations=[eq])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "inline-formula" in xml
        assert "eq1" in xml

    def test_block_equation(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        eq = MagicMock()
        eq.mathml = "<math><mi>y</mi></math>"
        eq.is_block = True
        eq.equation_id = "eq2"
        doc = self._make_doc(equations=[eq])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "disp-formula" in xml

    def test_bad_mathml_skips(self):
        from app.pipeline.export.jats_generator import JATSGenerator

        eq = MagicMock()
        eq.mathml = "<<<invalid>>>"
        eq.is_block = True
        eq.equation_id = "eq3"
        doc = self._make_doc(equations=[eq])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "disp-formula" in xml
