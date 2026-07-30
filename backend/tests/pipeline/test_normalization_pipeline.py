# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from app.models import PipelineDocument as Document
from app.models import PipelineDocument, Block, BlockType, ReviewStatus, TemplateInfo, Figure, Reference, Table, DocumentMetadata, Equation, TableCell, TextStyle, ImageFormat, BClass, EClass, RClass
from app.pipeline.formatting.formatter import Formatter
from __future__ import annotations
import pytest
from app.pipeline.normalization.normalizer import Normalizer

def _b(text: str, index: int, bid: str = None, bold: bool = False, font_size: float = 12.0):
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
    from app.models.block import TextStyle
    from app.models.table import TableCell

    return Block(
        block_id=bid or f"b{index}", text=text, index=index,
        block_type=BlockType.UNKNOWN,
        style=TextStyle(bold=bold, font_size=font_size),
    )

def _body(text: str, index: int, bid: str = None):
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
    return Block(
        block_id=bid or f"b{index}", text=text, index=index,
        block_type=BlockType.BODY,
    )

@pytest.fixture
def normalizer():
    from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
    return Normalizer()

class TestNormalizerProcess:
    def test_normalize_blocks_basic(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_b("Hello \u2014 world", 1)],
            metadata=DocumentMetadata(title="Test"),
        )
        result = normalizer.process(doc)
        assert len(result.blocks) == 1
        assert "Hello" in result.blocks[0].text

    def test_normalize_metadata_title(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(title="\u201cQuoted Title\u201d"),
        )
        result = normalizer.process(doc)
        assert '"' in result.metadata.title

    def test_normalize_metadata_authors(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(authors=["  Smith, J.  ", ""]),
        )
        result = normalizer.process(doc)
        assert len(result.metadata.authors) == 1
        assert result.metadata.authors[0] == "Smith, J."

    def test_normalize_metadata_abstract(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(abstract="  This   is   abstract.  "),
        )
        result = normalizer.process(doc)
        assert "  " not in result.metadata.abstract

    def test_normalize_metadata_keywords(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(keywords=["  ML  ", ""]),
        )
        result = normalizer.process(doc)
        assert len(result.metadata.keywords) == 1
        assert result.metadata.keywords[0] == "ML"

    def test_normalize_metadata_journal(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(journal="  IEEE Trans.  "),
        )
        result = normalizer.process(doc)
        assert result.metadata.journal == "IEEE Trans."

    def test_normalize_metadata_corresponding_author(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(corresponding_author="  Smith  "),
        )
        result = normalizer.process(doc)
        assert result.metadata.corresponding_author == "Smith"

    def test_normalize_metadata_email(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(email="  a@b.com  "),
        )
        result = normalizer.process(doc)
        assert result.metadata.email == "a@b.com"

class TestNormalizerSplitLogic:
    def test_abstract_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_b("AbstractThis paper presents...", 1)],
        )
        result = normalizer.process(doc)
        assert len(result.blocks) >= 2
        assert result.blocks[0].text == "Abstract"

    def test_numbered_heading_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_b("1 IntroductionScientific research is important...", 1)],
        )
        result = normalizer.process(doc)
        assert len(result.blocks) >= 2
        assert "1 Introduction" in result.blocks[0].text

    def test_numbered_heading_no_split_short_body(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_b("1 IntroductionHi", 1)],
        )
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

    def test_keyword_split(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_b("IntroductionThis research explores machine learning methods...", 1)],
        )
        result = normalizer.process(doc)
        assert len(result.blocks) >= 2
        assert result.blocks[0].text == "Introduction"

    def test_no_split_on_figure_block(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        doc = PipelineDocument(
            document_id="doc1",
            blocks=[_b("Figure 1. Results", 1, bid="f1")],
        )
        doc.blocks[0].metadata["has_figure"] = True
        result = normalizer.process(doc)
        assert len(result.blocks) == 1

class TestNormalizerTextRepair:
    def test_repair_ethodology(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        result = normalizer._repair_common_corruptions("2ethodology")
        assert result == "2 Methodology"

    def test_repair_ntroduction(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        result = normalizer._repair_common_corruptions("1ntroduction")
        assert result == "1 Introduction"

    def test_repair_esults(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        result = normalizer._repair_common_corruptions("3esults")
        assert result == "3 Results"

    def test_repair_empty(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        assert normalizer._repair_common_corruptions("") == ""

    def test_repair_no_change(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        assert normalizer._repair_common_corruptions("Normal text") == "Normal text"

class TestNormalizerTables:
    def test_normalize_table_cells(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        cell = TableCell(text="  Hello  \nworld  ", row=0, col=0)
        table = Table(
            table_id="t1", num_rows=1, num_cols=1, index=1, block_index=0,
            cells=[cell],
            rows=[["  Hello  \nworld  "]],
        )
        doc = PipelineDocument(document_id="doc1", tables=[table])
        result = normalizer.process(doc)
        assert result.tables[0].cells[0].text == "Hello world"
        assert result.tables[0].rows[0][0] == "Hello world"

    def test_normalize_table_caption(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        table = Table(
            table_id="t1", num_rows=1, num_cols=1, index=1, block_index=0,
            caption_text="  Table caption  ",
        )
        doc = PipelineDocument(document_id="doc1", tables=[table])
        result = normalizer.process(doc)
        assert result.tables[0].caption_text == "Table caption"

class TestNormalizerBlockSplittingMultiLine:
    def test_consecutive_heading_merge(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        blocks = [
            _b("Introduction", 1, bold=True, font_size=14.0),
            _b("Background", 2, bold=True, font_size=14.0),
            _b("Some body text.", 3),
        ]
        doc = PipelineDocument(document_id="doc1", blocks=blocks)
        result = normalizer.process(doc)
        assert len(result.blocks) <= 2

    def test_duplicate_blocks_removed(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        blocks = [
            _b("Same text", 1),
            _b("Same text", 2),
            _b("Different", 3),
        ]
        doc = PipelineDocument(document_id="doc1", blocks=blocks)
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

    def test_duplicate_blocks_not_identical_style(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        from app.models.block import TextStyle
        b1 = Block(block_id="b1", text="Intro", index=1, block_type=BlockType.UNKNOWN, style=TextStyle(bold=True))
        b2 = Block(block_id="b2", text="Intro", index=2, block_type=BlockType.UNKNOWN, style=TextStyle(bold=False))
        doc = PipelineDocument(document_id="doc1", blocks=[b1, b2])
        result = normalizer.process(doc)
        assert len(result.blocks) == 2

class TestNormalizerEmptyOrphanRemoval:
    def test_empty_body_block_removed(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        blocks = [_body("", 1), _body("Content", 2)]
        doc = PipelineDocument(document_id="doc1", blocks=blocks)
        result = normalizer._sanitize_empty_orphan_blocks(blocks)
        assert len(result) == 1

    def test_empty_block_with_figure_preserved(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        block = _body("", 1, bid="b1")
        block.metadata["has_figure"] = True
        result = normalizer._sanitize_empty_orphan_blocks([block])
        assert len(result) == 1

    def test_empty_block_with_equation_preserved(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        block = _body("", 1, bid="b1")
        block.metadata["has_equation"] = True
        result = normalizer._sanitize_empty_orphan_blocks([block])
        assert len(result) == 1

    def test_empty_block_with_list_level_preserved(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        block = _body("", 1, bid="b1")
        block.metadata["list_level"] = 1
        result = normalizer._sanitize_empty_orphan_blocks([block])
        assert len(result) == 1

    def test_non_empty_body_preserved(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        block = _body("Content", 1)
        result = normalizer._sanitize_empty_orphan_blocks([block])
        assert len(result) == 1

    def test_empty_non_body_preserved(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        block = Block(block_id="b1", text="", index=1, block_type=BlockType.HEADING_1)
        result = normalizer._sanitize_empty_orphan_blocks([block])
        assert len(result) == 1

class TestNormalizerMedianFont:
    def test_median_font_with_blocks(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        blocks = [
            _b("A", 1, font_size=10.0),
            _b("B", 2, font_size=12.0),
            _b("C", 3, font_size=14.0),
        ]
        median = normalizer._calculate_median_font_size(blocks)
        assert median == 12.0

    def test_median_font_no_blocks(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        assert normalizer._calculate_median_font_size([]) is None

    def test_median_font_no_text_blocks_excluded(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        blocks = [_b("", 1, font_size=10.0), _b("A", 2, font_size=12.0)]
        median = normalizer._calculate_median_font_size(blocks)
        assert median == 12.0

class TestNormalizerConvenience:
    def test_normalize_document_convenience(self, normalizer):
        from app.models import PipelineDocument, Block, BlockType, DocumentMetadata, Table
        from app.pipeline.normalization.normalizer import normalize_document
        doc = PipelineDocument(
            document_id="doc1",
            metadata=DocumentMetadata(title="  Test  "),
        )
        result = normalize_document(doc)
        assert result.metadata.title == "Test"
