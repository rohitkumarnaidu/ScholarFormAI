import pytest
from unittest.mock import MagicMock
from datetime import datetime


@pytest.fixture
def doc():
    doc = MagicMock()
    doc.metadata.title = "Test Paper"
    doc.metadata.authors = ["Alice Smith"]
    doc.metadata.publication_date = datetime(2024, 6, 15)
    doc.metadata.volume = "12"
    doc.metadata.issue = "3"
    doc.metadata.abstract = "This is a test abstract."
    doc.blocks = []
    doc.references = []
    doc.equations = []
    return doc


class TestJATSGenerator:
    def test_basic_xml(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "<article" in xml
        assert "Test Paper" in xml
        assert "Alice" in xml and "Smith" in xml
        assert "2024" in xml
        assert "test abstract" in xml

    def test_no_authors_adds_placeholder(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        doc.metadata.authors = []
        xml = gen.to_xml(doc)
        assert "Unknown" in xml or "Author" in xml

    def test_references(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        ref = MagicMock()
        ref.reference_id = "ref1"
        ref.raw_text = "Smith, J. (2020). A paper."
        ref.metadata = {"doi": "10.1234/abc"}
        doc.references = [ref]
        xml = gen.to_xml(doc)
        assert "ref-list" in xml
        assert "Smith, J." in xml
        assert "10.1234/abc" in xml

    def test_no_references(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        doc.references = []
        xml = gen.to_xml(doc)
        assert "ref-list" not in xml

    def test_blocks_in_body(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        block = MagicMock()
        block.text = "Introduction content"
        block.metadata = {"semantic_intent": "body"}
        doc.blocks = [block]
        xml = gen.to_xml(doc)
        assert "Introduction content" in xml

    def test_heading_creates_sec(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        heading = MagicMock()
        heading.text = "Methods"
        heading.metadata = {"semantic_intent": "heading"}
        body = MagicMock()
        body.text = "We did stuff."
        body.metadata = {"semantic_intent": "body"}
        doc.blocks = [heading, body]
        xml = gen.to_xml(doc)
        assert "<title>Methods</title>" in xml

    def test_equation_with_mathml(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        eq = MagicMock()
        eq.mathml = "<mml:math><mml:mi>x</mml:mi></mml:math>"
        eq.is_block = True
        eq.equation_id = "eq1"
        doc.equations = [eq]
        xml = gen.to_xml(doc)
        assert "disp-formula" in xml
        assert "mml:math" in xml or "x" in xml

    def test_publication_date_string(self, doc):
        from app.pipeline.export.jats_generator import JATSGenerator
        gen = JATSGenerator()
        doc.metadata.publication_date = "2024-06-15"
        xml = gen.to_xml(doc)
        assert "2024" in xml
