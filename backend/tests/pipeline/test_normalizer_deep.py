# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep test suite for Normalizer pipeline stage.
Covers process(), metadata normalization, block repair/splitting/consolidation,
table normalization, empty orphan sanitization, median font calculation.
"""

from __future__ import annotations
import pytest
from app.pipeline.normalization.normalizer import Normalizer, normalize_document

@pytest.fixture
def normalizer():

    return Normalizer()

@pytest.fixture
def minimal_doc():
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata
    meta = DocumentMetadata(title="Test  Manuscript", authors=["  John  Doe  "], abstract="  Hello world.  ")
    doc = PipelineDocument(document_id="n1", metadata=meta, blocks=[
        Block(block_id="b1", index=0, text="  Introduction  ", block_type=BlockType.UNKNOWN),
        Block(block_id="b2", index=1, text="This is body text with smart quotes \u201cHello\u201d.", block_type=BlockType.UNKNOWN),
    ])
    return doc

class TestNormalizerProcess:
    def test_process_normalizes_all_content(self, normalizer, minimal_doc):
        result = normalizer.process(minimal_doc)
        assert result.metadata.title == "Test Manuscript"
        assert "John Doe" in result.metadata.authors
        assert result.blocks[0].text == "Introduction"
        assert "\"" in result.blocks[1].text
        assert result.updated_at is not None

    def test_process_empty_document(self, normalizer):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="empty", blocks=[])
        result = normalizer.process(doc)
        assert len(result.blocks) == 0

    def test_process_duplicate_indices_raises(self, normalizer):
        from app.models import PipelineDocument, Block
        doc = PipelineDocument(document_id="dup", blocks=[
            Block(block_id="a", index=0, text="A"),
            Block(block_id="b", index=0, text="B"),
        ])
        with pytest.raises(AssertionError, match="Duplicate block indices"):
            normalizer.process(doc)

class TestNormalizeMetadata:
    def test_title_cleaned(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        doc = PipelineDocument(document_id="t1", metadata=DocumentMetadata(title="  Hello   World  "))
        normalizer.process(doc)
        assert doc.metadata.title == "Hello World"

    def test_authors_filtered(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(authors=["  Alice  ", "", "  Bob  "])
        doc = PipelineDocument(document_id="t2", metadata=meta)
        normalizer.process(doc)
        assert doc.metadata.authors == ["Alice", "Bob"]

    def test_affiliations_cleaned(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(affiliations=["  Univ   A  ", ""])
        doc = PipelineDocument(document_id="t3", metadata=meta)
        normalizer.process(doc)
        assert doc.metadata.affiliations == ["Univ A"]

    def test_abstract_normalized(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(abstract="  Line1\n  Line2  ")
        doc = PipelineDocument(document_id="t4", metadata=meta)
        normalizer.process(doc)
        assert "Line1" in doc.metadata.abstract

    def test_keywords_cleaned(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(keywords=["  ML  ", "", " NLP  "])
        doc = PipelineDocument(document_id="t5", metadata=meta)
        normalizer.process(doc)
        assert doc.metadata.keywords == ["ML", "NLP"]

    def test_journal_cleaned(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(journal="  Nature   Communications  ")
        doc = PipelineDocument(document_id="t6", metadata=meta)
        normalizer.process(doc)
        assert doc.metadata.journal == "Nature Communications"

    def test_corresponding_author_cleaned(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(corresponding_author="  Jane   Smith  ")
        doc = PipelineDocument(document_id="t7", metadata=meta)
        normalizer.process(doc)
        assert doc.metadata.corresponding_author == "Jane Smith"

    def test_email_cleaned(self, normalizer):
        from app.models import PipelineDocument, DocumentMetadata
        meta = DocumentMetadata(email="  test@example.com  ")
        doc = PipelineDocument(document_id="t8", metadata=meta)
        normalizer.process(doc)
        assert doc.metadata.email == "test@example.com"

class TestBlockRepair:
    def test_repair_ntroduction(self, normalizer):
        assert normalizer._repair_common_corruptions("1ntroduction") == "1 Introduction"

    def test_repair_ethodology(self, normalizer):
        assert normalizer._repair_common_corruptions("2ethodology") == "2 Methodology"

    def test_repair_esults(self, normalizer):
        assert normalizer._repair_common_corruptions("3esults") == "3 Results"

    def test_repair_iscussion(self, normalizer):
        assert normalizer._repair_common_corruptions("4iscussion") == "4 Discussion"

    def test_repair_onclusion(self, normalizer):
        assert normalizer._repair_common_corruptions("5onclusion") == "5 Conclusion"

    def test_repair_eferences(self, normalizer):
        assert normalizer._repair_common_corruptions("6eferences") == "6 References"

    def test_repair_bstract(self, normalizer):
        assert normalizer._repair_common_corruptions("7bstract") == "7 Abstract"

    def test_repair_empty_string(self, normalizer):
        assert normalizer._repair_common_corruptions("") == ""

    def test_repair_no_match_preserves(self, normalizer):
        assert normalizer._repair_common_corruptions("Normal text here.") == "Normal text here."

class TestAbstractSplit:
    def test_abstract_colon_body(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="ab1", blocks=[
            Block(block_id="b1", index=0, text="Abstract: This paper presents a novel method.", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2
        assert result.blocks[0].text == "Abstract"
        assert result.blocks[1].text == "This paper presents a novel method."

    def test_abstract_dash_body(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="ab2", blocks=[
            Block(block_id="b1", index=0, text="Abstract \u2014 The system achieves high accuracy.", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_abstract_no_delimiter(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        text = "AbstractThe system is described in this manuscript with extensive details."
        doc = PipelineDocument(document_id="ab3", blocks=[
            Block(block_id="b1", index=0, text=text, block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_abstract_standalone_not_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="ab4", blocks=[
            Block(block_id="b1", index=0, text="Abstract", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].text == "Abstract"

class TestNumberedHeadingSplit:
    def test_numbered_heading_with_body(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="nh1", blocks=[
            Block(block_id="b1", index=0, text="1 IntroductionThis section introduces the topic and background.", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2
        assert "Introduction" in result.blocks[0].text

    def test_numbered_heading_no_body_not_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="nh2", blocks=[
            Block(block_id="b1", index=0, text="1 Introduction", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

    def test_numbered_heading_short_body_not_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="nh3", blocks=[
            Block(block_id="b1", index=0, text="1 IntroductionShort.", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

    def test_list_item_not_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="nh4", blocks=[
            Block(block_id="b1", index=0, text="1. First item in a list", block_type=BlockType.UNKNOWN,
                  metadata={"list_level": 1}),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

class TestKeywordSplit:
    def test_keyword_merged_with_body(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="kw1", blocks=[
            Block(block_id="b1", index=0, text="IntroductionThis section provides background on the topic and reviews related work in the field.", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_keyword_short_body_not_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="kw2", blocks=[
            Block(block_id="b1", index=0, text="IntroductionShort.", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

class TestFigureBlockPreservation:
    def test_figure_block_not_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="fig1", blocks=[
            Block(block_id="b1", index=0, text="Figure 1. Architecture diagram", block_type=BlockType.UNKNOWN,
                  metadata={"has_figure": True}),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

    def test_empty_figure_block_kept(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="fig2", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.UNKNOWN,
                  metadata={"has_figure": True}),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

class TestMultiLineHeadingConsolidation:
    def test_consolidate_two_headings(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        from app.models.block import TextStyle
        style_a = TextStyle(bold=True, font_size=14.0)
        style_b = TextStyle(bold=True, font_size=13.0)
        doc = PipelineDocument(document_id="ml1", blocks=[
            Block(block_id="b1", index=0, text="Related", block_type=BlockType.UNKNOWN, style=style_a),
            Block(block_id="b2", index=1, text="Work", block_type=BlockType.UNKNOWN, style=style_b),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].text == "Related Work"

    def test_no_consolidation_with_period(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        from app.models.block import TextStyle
        style = TextStyle(bold=True, font_size=14.0)
        doc = PipelineDocument(document_id="ml2", blocks=[
            Block(block_id="b1", index=0, text="Related.", block_type=BlockType.UNKNOWN, style=style),
            Block(block_id="b2", index=1, text="Work.", block_type=BlockType.UNKNOWN, style=style),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_no_consolidation_non_bold(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="ml3", blocks=[
            Block(block_id="b1", index=0, text="Related", block_type=BlockType.UNKNOWN),
            Block(block_id="b2", index=1, text="Work", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_no_consolidation_long_headings(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        from app.models.block import TextStyle
        style = TextStyle(bold=True, font_size=14.0)
        doc = PipelineDocument(document_id="ml4", blocks=[
            Block(block_id="b1", index=0, text="A" * 90, block_type=BlockType.UNKNOWN, style=style),
            Block(block_id="b2", index=1, text="B" * 90, block_type=BlockType.UNKNOWN, style=style),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_no_consolidation_multiple_bold(self, normalizer):
        from app.models import PipelineDocument, Block
        from app.models.block import TextStyle
        style = TextStyle(bold=True, font_size=14.0)
        doc = PipelineDocument(document_id="ml5", blocks=[
            Block(block_id="b1", index=0, text="Related", style=style),
            Block(block_id="b2", index=1, text="Work", style=style),
            Block(block_id="b3", index=2, text="Review", style=style),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

class TestConsecutiveDuplicateFilter:
    def test_identical_blocks_suppressed(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="cd1", blocks=[
            Block(block_id="b1", index=0, text="Duplicate text", block_type=BlockType.UNKNOWN),
            Block(block_id="b2", index=1, text="Duplicate text", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

    def test_different_blocks_preserved(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="cd2", blocks=[
            Block(block_id="b1", index=0, text="First", block_type=BlockType.UNKNOWN),
            Block(block_id="b2", index=1, text="Second", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_empty_duplicates_removed(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="cd3", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.UNKNOWN),
            Block(block_id="b2", index=1, text="", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert len(result.blocks) == 0

    def test_duplicate_tracking_in_metadata(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="cd4", blocks=[
            Block(block_id="b1", index=0, text="Hello", block_type=BlockType.UNKNOWN),
            Block(block_id="b2", index=1, text="Hello", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer.process(doc)
        assert result.blocks[0].metadata.get("has_consecutive_duplicate") is True

class TestEmptyOrphanSanitization:
    def test_empty_body_removed(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo1", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.BODY),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 0

    def test_empty_unknown_removed(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo2", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.UNKNOWN),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 0

    def test_empty_with_figure_kept(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo3", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.BODY,
                  metadata={"has_figure": True}),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 1

    def test_empty_with_equation_kept(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo4", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.BODY,
                  metadata={"has_equation": True}),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 1

    def test_empty_with_list_level_kept(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo5", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.BODY,
                  metadata={"list_level": 1}),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 1

    def test_non_empty_body_kept(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo6", blocks=[
            Block(block_id="b1", index=0, text="Content", block_type=BlockType.BODY),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 1

    def test_heading_empty_kept(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType
        doc = PipelineDocument(document_id="eo7", blocks=[
            Block(block_id="b1", index=0, text="", block_type=BlockType.HEADING_1),
        ])
        result = normalizer._sanitize_empty_orphan_blocks(doc.blocks)
        assert len(result) == 1

class TestTableNormalization:
    def test_table_cells_normalized(self, normalizer):
        from app.models import PipelineDocument, Table, TableCell
        doc = PipelineDocument(document_id="tb1", tables=[
            Table(table_id="t1", num_rows=2, num_cols=2, index=0, block_index=0,
                  cells=[TableCell(row=0, col=0, text="  A  ")],
                  rows=[["  B  "]]),
        ])
        normalizer.process(doc)
        assert doc.tables[0].cells[0].text == "A"
        assert doc.tables[0].rows[0][0] == "B"

    def test_table_caption_normalized(self, normalizer):
        from app.models import PipelineDocument, Table
        doc = PipelineDocument(document_id="tb2", tables=[
            Table(table_id="t1", num_rows=1, num_cols=1, index=0, block_index=1,
                  caption_text="  Table  1  ", cells=[], rows=[]),
        ])
        normalizer.process(doc)
        assert doc.tables[0].caption_text == "Table 1"

    def test_no_tables_does_not_crash(self, normalizer):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="tb3")
        result = normalizer.process(doc)
        assert result.document_id == "tb3"

class TestMedianFontSize:
    def test_median_calculated(self, normalizer):
        from app.models import Block
        from app.models.block import TextStyle
        blocks = [
            Block(block_id="b1", index=0, text="A", style=TextStyle(font_size=10.0)),
            Block(block_id="b2", index=1, text="B", style=TextStyle(font_size=12.0)),
            Block(block_id="b3", index=2, text="C", style=TextStyle(font_size=14.0)),
        ]
        result = normalizer._calculate_median_font_size(blocks)
        assert result == 12.0

    def test_median_no_text_returns_none(self, normalizer):
        from app.models import Block
        from app.models.block import TextStyle
        blocks = [
            Block(block_id="b1", index=0, text="", style=TextStyle(font_size=10.0)),
        ]
        result = normalizer._calculate_median_font_size(blocks)
        assert result is None

    def test_median_no_font_size_returns_none(self, normalizer):
        from app.models import Block
        blocks = [Block(block_id="b1", index=0, text="Hello")]
        result = normalizer._calculate_median_font_size(blocks)
        assert result is None

class TestConvenienceFunction:
    def test_normalize_document_wrapper(self, minimal_doc):
        result = normalize_document(minimal_doc)
        assert result.metadata.title == "Test Manuscript"

    def test_normalize_document_empty(self):
        from app.models import PipelineDocument
        doc = PipelineDocument(document_id="empty")
        result = normalize_document(doc)
        assert result.document_id == "empty"

class TestProcessingHistory:
    def test_processing_stage_added(self, normalizer, minimal_doc):
        result = normalizer.process(minimal_doc)
        assert len(result.processing_history) >= 1
        stage = result.processing_history[-1]
        assert stage.stage_name == "normalization"
        assert stage.status == "success"

    def test_duration_recorded(self, normalizer, minimal_doc):
        result = normalizer.process(minimal_doc)
        stage = result.processing_history[-1]
        assert stage.duration_ms >= 0
