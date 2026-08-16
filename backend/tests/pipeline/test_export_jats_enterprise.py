# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from datetime import datetime

from app.models import Block as BClass
from app.models import Equation as EClass
from app.models import Reference as RClass
from app.pipeline.export.jats_generator import JATSGenerator


def _make_doc(**overrides):
    from app.models import Block, BlockType, PipelineDocument, Reference
    from app.models.pipeline_document import DocumentMetadata, TemplateInfo

    defaults = dict(
        document_id="jats1",
        blocks=[
            Block(
                block_id="b1",
                index=1,
                block_type=BlockType.TITLE,
                text="Paper Title",
                section_name="title",
                metadata={"semantic_intent": "heading"},
            ),
            Block(
                block_id="b2",
                index=2,
                block_type=BlockType.BODY,
                text="Body content.",
                section_name="body",
                metadata={"semantic_intent": "body"},
            ),
        ],
        metadata=DocumentMetadata(
            title="Test Paper",
            authors=["Alice Smith", "Bob Jones"],
            abstract="This is a test abstract.",
            keywords=["test", "paper"],
            publication_date=datetime(2024, 6, 15),
            volume="10",
            issue="2",
        ),
        template=TemplateInfo(template_name="default"),
        equations=[],
        references=[
            Reference(
                reference_id="r1",
                index=1,
                block_id="r1",
                block_index=1,
                citation_key="alice2024",
                year="2024",
                authors=["Alice"],
                title="A paper",
                raw_text="[1] Alice et al. (2024)",
            ),
        ],
    )
    defaults.update(overrides)
    doc = PipelineDocument(**{k: v for k, v in defaults.items() if k != "template"})
    doc.template = defaults["template"]
    return doc


class TestJATSGenerator:
    # ── to_xml ──────────────────────────────────────────────────────────

    def test_to_xml_basic(self):
        gen = JATSGenerator()
        xml = gen.to_xml(_make_doc())
        assert xml.startswith("<!DOCTYPE article")
        assert "<article" in xml
        assert "<article-title>Test Paper</article-title>" in xml
        assert "<surname>Smith</surname>" in xml
        assert "<given-names>Alice</given-names>" in xml
        assert "<year>2024</year>" in xml

    def test_to_xml_no_blocks(self):
        gen = JATSGenerator()
        xml = gen.to_xml(_make_doc(blocks=[]))
        assert "<body/>" in xml
        assert "<back>" in xml

    def test_to_xml_empty_metadata(self):
        doc = _make_doc()
        doc.metadata.title = None
        doc.metadata.authors = []
        doc.metadata.abstract = None
        doc.metadata.publication_date = None
        doc.metadata.volume = None
        doc.metadata.issue = None
        doc.references = []
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "Untitled Manuscript" in xml
        assert "<given-names>Unknown</given-names>" in xml

    def test_to_xml_special_chars(self):
        doc = _make_doc()
        doc.metadata.title = 'Title & <Special> "Chars"'
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "Title" in xml

    def test_to_xml_no_references(self):
        doc = _make_doc(references=[])
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "ref-list" not in xml

    def test_to_xml_unicode_text(self):
        doc = _make_doc()
        doc.metadata.authors = ["José García", " 伟"]
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "José" in xml

    # ── _add_references ─────────────────────────────────────────────────

    def test_refs_empty_list(self):
        doc = _make_doc(references=[])
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)
        assert len(list(parent)) == 0

    def test_refs_with_raw_text(self):
        doc = _make_doc()
        doc.references[0].raw_text = "[1] Smith et al. 2024"
        doc.references[0].metadata = {}
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)
        ref_list = parent[0]
        assert ref_list.tag == "ref-list"
        assert ref_list[1][0].text == "[1] Smith et al. 2024"

    def test_refs_with_doi_in_metadata(self):
        doc = _make_doc()
        doc.references[0].metadata = {"doi": "10.1234/test"}
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)
        mixed = parent[0][1][0]
        found = any(p.text == "10.1234/test" for p in mixed.findall("pub-id"))
        assert found

    def test_refs_without_raw_text(self):
        doc = _make_doc()
        doc.references[0].raw_text = None
        doc.references[0].metadata = {}
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)
        assert parent[0][1][0].text == "Reference text unavailable"

    def test_refs_without_reference_id(self):
        doc = _make_doc()
        doc.references[0].reference_id = None
        doc.references[0].metadata = {}
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)
        assert parent[0][1].attrib.get("id", "").startswith("ref_")

    def test_refs_no_doi_in_metadata(self):
        doc = _make_doc()
        doc.references[0].metadata = {"some_key": "value"}
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)
        assert len(parent[0][1][0].findall("pub-id")) == 0

    def test_refs_metadata_none(self):
        doc = _make_doc()
        doc.references[0].metadata = None
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("back")
        gen._add_references(parent, doc)

    # ── _add_metadata ────────────────────────────────────────────────────

    def test_metadata_title_missing(self):
        doc = _make_doc()
        doc.metadata.title = None
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "Untitled Manuscript" in etree.tostring(parent, encoding="unicode")

    def test_metadata_authors_empty(self):
        doc = _make_doc()
        doc.metadata.authors = []
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "<given-names>Unknown</given-names>" in etree.tostring(parent, encoding="unicode")

    def test_metadata_single_author(self):
        doc = _make_doc()
        doc.metadata.authors = ["JohnDoe"]
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "<surname>JohnDoe</surname>" in xml
        assert "<given-names>JohnDoe</given-names>" in xml

    def test_metadata_author_name_parsing(self):
        doc = _make_doc()
        doc.metadata.authors = ["John A. Doe III"]
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "<surname>III</surname>" in etree.tostring(parent, encoding="unicode")

    def test_metadata_pub_date_datetime(self):
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, _make_doc())
        xml = etree.tostring(parent, encoding="unicode")
        assert "<year>2024</year>" in xml
        assert "<month>06</month>" in xml
        assert "<day>15</day>" in xml

    def test_metadata_pub_date_string(self):
        doc = _make_doc()
        doc.metadata.publication_date = "2023-05-20"
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "<year>2023</year>" in xml
        assert "<month>05</month>" in xml
        assert "<day>20</day>" in xml

    def test_metadata_pub_date_string_malformed(self):
        doc = _make_doc()
        doc.metadata.publication_date = "invalid-date"
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        etree.tostring(parent, encoding="unicode")

    def test_metadata_pub_date_none(self):
        doc = _make_doc()
        doc.metadata.publication_date = None
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "pub-date" not in etree.tostring(parent, encoding="unicode")

    def test_metadata_pub_date_string_partial(self):
        doc = _make_doc()
        doc.metadata.publication_date = "2023"
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "<year>2023</year>" in xml
        assert "<month>" not in xml

    def test_metadata_pub_date_string_two_parts(self):
        doc = _make_doc()
        doc.metadata.publication_date = "2023-08"
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "<year>2023</year>" in xml
        assert "<month>08</month>" in xml

    def test_volume_present(self):
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, _make_doc())
        assert "<volume>10</volume>" in etree.tostring(parent, encoding="unicode")

    def test_volume_absent(self):
        doc = _make_doc()
        doc.metadata.volume = None
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "<volume>" not in etree.tostring(parent, encoding="unicode")

    def test_issue_present(self):
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, _make_doc())
        assert "<issue>2</issue>" in etree.tostring(parent, encoding="unicode")

    def test_issue_absent(self):
        doc = _make_doc()
        doc.metadata.issue = None
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "<issue>" not in etree.tostring(parent, encoding="unicode")

    def test_abstract_present(self):
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, _make_doc())
        xml = etree.tostring(parent, encoding="unicode")
        assert "<abstract>" in xml
        assert "This is a test abstract." in xml

    def test_abstract_absent(self):
        doc = _make_doc()
        doc.metadata.abstract = None
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "<abstract>" not in etree.tostring(parent, encoding="unicode")

    # ── _add_body ────────────────────────────────────────────────────────

    def test_body_no_blocks(self):
        doc = _make_doc(blocks=[])
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("body")
        gen._add_body(parent, doc)
        assert "<body/>" in etree.tostring(parent, encoding="unicode")

    def test_body_heading_block(self):
        from lxml import etree

        from app.models import BlockType

        doc = _make_doc()
        doc.blocks = [
            BClass(
                block_id="b1",
                index=1,
                block_type=BlockType.TITLE,
                text="Heading",
                section_name="title",
                metadata={"semantic_intent": "heading"},
            )
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "<sec>" in xml
        assert "<title>" in xml

    def test_body_body_block(self):
        from app.models import BlockType

        doc = _make_doc()
        from lxml import etree

        doc.blocks = [
            BClass(
                block_id="b1",
                index=1,
                block_type=BlockType.BODY,
                text="Body text",
                section_name="body",
                metadata={"semantic_intent": "body"},
            )
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        assert "<p>" in etree.tostring(parent, encoding="unicode")

    def test_body_mixed_blocks(self):
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("body")
        gen._add_body(parent, _make_doc())
        xml = etree.tostring(parent, encoding="unicode")
        assert "<sec>" in xml
        assert "<p>" in xml

    def test_body_body_before_heading(self):
        from lxml import etree

        from app.models import BlockType

        doc = _make_doc()
        doc.blocks = [
            BClass(
                block_id="b1",
                index=1,
                block_type=BlockType.BODY,
                text="First text",
                section_name="body",
                metadata={"semantic_intent": "body"},
            ),
            BClass(
                block_id="b2",
                index=2,
                block_type=BlockType.HEADING_1,
                text="Late heading",
                section_name="section",
                metadata={"semantic_intent": "heading"},
            ),
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "<p>First text</p>" in xml
        assert "<sec>" in xml

    def test_body_block_no_semantic_intent(self):
        from lxml import etree

        from app.models import BlockType

        doc = _make_doc()
        doc.blocks = [
            BClass(
                block_id="b1", index=1, block_type=BlockType.BODY, text="Default body", section_name="body", metadata={}
            )
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        assert "<p>Default body</p>" in etree.tostring(parent, encoding="unicode")

    def test_body_equations_disp_formula(self):
        from lxml import etree

        doc = _make_doc()
        doc.equations = [
            EClass(
                equation_id="eq1",
                index=1,
                block_id="b1",
                mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>x</mi></math>",
                is_block=True,
            )
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        assert "disp-formula" in etree.tostring(parent, encoding="unicode")

    def test_body_equations_inline_formula(self):
        from lxml import etree

        doc = _make_doc()
        doc.equations = [
            EClass(
                equation_id="eq2",
                index=2,
                block_id="b2",
                mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>y</mi></math>",
                is_block=False,
            )
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        assert "inline-formula" in etree.tostring(parent, encoding="unicode")

    def test_body_equations_no_mathml(self):
        from lxml import etree

        doc = _make_doc()
        doc.equations = [EClass(equation_id="eq3", index=3, block_id="b3", mathml=None, is_block=True)]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        etree.tostring(parent, encoding="unicode")

    def test_body_equation_malformed_mathml(self):
        from lxml import etree

        doc = _make_doc()
        doc.equations = [EClass(equation_id="eq4", index=4, block_id="b4", mathml="<<<malformed>>>", is_block=True)]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        etree.tostring(parent, encoding="unicode")

    def test_body_multiple_equations(self):
        from lxml import etree

        doc = _make_doc()
        doc.equations = [
            EClass(
                equation_id="eq1",
                index=1,
                block_id="b1",
                mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>a</mi></math>",
                is_block=True,
            ),
            EClass(
                equation_id="eq2",
                index=2,
                block_id="b2",
                mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>b</mi></math>",
                is_block=False,
            ),
        ]
        gen = JATSGenerator()
        parent = etree.Element("body")
        gen._add_body(parent, doc)
        assert "disp-formula" in etree.tostring(parent, encoding="unicode")
        assert "inline-formula" in etree.tostring(parent, encoding="unicode")

    # ── XML validity ─────────────────────────────────────────────────────

    def test_output_is_valid_xml(self):
        gen = JATSGenerator()
        from lxml import etree

        root = etree.fromstring(gen.to_xml(_make_doc()).encode())
        assert root.tag == "article"

    def test_output_has_namespaces(self):
        gen = JATSGenerator()
        xml = gen.to_xml(_make_doc())
        assert "http://www.w3.org/1998/Math/MathML" in xml

    def test_output_dtd_declaration(self):
        gen = JATSGenerator()
        xml = gen.to_xml(_make_doc())
        assert "DOCTYPE" in xml
        assert "JATS-archivearticle1.dtd" in xml

    def test_output_article_type_attribute(self):
        gen = JATSGenerator()
        from lxml import etree

        root = etree.fromstring(gen.to_xml(_make_doc()).encode())
        assert root.attrib.get("article-type") == "research-article"

    def test_output_dtd_version_attribute(self):
        gen = JATSGenerator()
        from lxml import etree

        root = etree.fromstring(gen.to_xml(_make_doc()).encode())
        assert root.attrib.get("dtd-version") == "1.2"

    # ── Edge cases ───────────────────────────────────────────────────────

    def test_metadata_volume_zero(self):
        doc = _make_doc()
        doc.metadata.volume = "0"
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "<volume>0</volume>" in etree.tostring(parent, encoding="unicode")

    def test_metadata_long_author_list(self):
        doc = _make_doc()
        doc.metadata.authors = [f"Author {i}" for i in range(20)]
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        xml = etree.tostring(parent, encoding="unicode")
        assert "Author" in xml

    def test_metadata_empty_keywords_no_crash(self):
        doc = _make_doc()
        doc.metadata.keywords = []
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert isinstance(xml, str)

    def test_no_affiliations(self):
        doc = _make_doc()
        doc.metadata.affiliations = []
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert isinstance(xml, str)

    def test_reference_list_multi(self):
        doc = _make_doc()
        doc.references = [
            RClass(
                reference_id="r1",
                block_id="r1",
                block_index=1,
                index=1,
                citation_key="a2024",
                year="2024",
                authors=["A"],
                title="Paper A",
                raw_text="[1] A",
                metadata={},
            ),
            RClass(
                reference_id="r2",
                block_id="r2",
                block_index=2,
                index=2,
                citation_key="b2024",
                year="2024",
                authors=["B"],
                title="Paper B",
                raw_text="[2] B",
                metadata={"doi": "10.1234/b"},
            ),
        ]
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert "[1] A" in xml
        assert "[2] B" in xml

    def test_body_section_heading_without_text(self):
        from app.models import BlockType

        doc = _make_doc()
        doc.blocks = [
            BClass(
                block_id="b1",
                index=1,
                block_type=BlockType.HEADING_1,
                text="",
                section_name="section",
                metadata={"semantic_intent": "heading"},
            ),
        ]
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert isinstance(xml, str)

    def test_publication_date_empty_string(self):
        doc = _make_doc()
        doc.metadata.publication_date = ""
        gen = JATSGenerator()
        from lxml import etree

        parent = etree.Element("front")
        gen._add_metadata(parent, doc)
        assert "pub-date" not in etree.tostring(parent, encoding="unicode")

    def test_reference_raw_text_empty_string(self):
        doc = _make_doc()
        doc.references[0].raw_text = ""
        doc.references[0].metadata = {}
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert isinstance(xml, str)

    def test_body_equation_empty_mathml_string(self):
        doc = _make_doc()
        doc.equations = [EClass(equation_id="eq1", index=1, block_id="b1", mathml="", is_block=True)]
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert isinstance(xml, str)

    def test_generator_multiple_calls(self):
        gen = JATSGenerator()
        xml1 = gen.to_xml(_make_doc(document_id="doc1"))
        xml2 = gen.to_xml(_make_doc(document_id="doc2"))
        assert isinstance(xml1, str)
        assert isinstance(xml2, str)

    def test_metadata_journal_present(self):
        doc = _make_doc()
        doc.metadata.journal = "Test Journal"
        gen = JATSGenerator()
        xml = gen.to_xml(doc)
        assert isinstance(xml, str)
