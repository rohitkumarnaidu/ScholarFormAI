from unittest.mock import MagicMock
from app.models.block import Block, BlockType


def _mkblock(text="Some text", btype=BlockType.BODY, idx=0, bid="b1"):
    return Block(block_id=bid, text=text, block_type=btype, index=idx)


class TestFindReferencesStartIndex:
    def test_finds_by_block_type(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        blocks = [
            _mkblock("Intro", BlockType.HEADING_1, 0, "b1"),
            _mkblock("References", BlockType.REFERENCES_HEADING, 1, "b2"),
            _mkblock("[1] Ref A", BlockType.REFERENCE_ENTRY, 2, "b3"),
        ]
        result = matcher._find_references_start_index(blocks)
        assert result == 1

    def test_finds_by_keyword_fallback(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        blocks = [
            _mkblock("Intro", BlockType.HEADING_1, 0, "b1"),
            _mkblock("References", BlockType.HEADING_1, 1, "b2"),
        ]
        result = matcher._find_references_start_index(blocks)
        assert result == 1

    def test_bibliography_keyword(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        blocks = [
            _mkblock("Bibliography", BlockType.HEADING_1, 0, "b1"),
        ]
        result = matcher._find_references_start_index(blocks)
        assert result == 0

    def test_no_references_found(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        blocks = [
            _mkblock("Intro", BlockType.HEADING_1, 0, "b1"),
            _mkblock("Conclusion", BlockType.HEADING_1, 1, "b2"),
        ]
        result = matcher._find_references_start_index(blocks)
        assert result is None


class TestCaptionRegex:
    def test_matches_numeric(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        assert matcher.caption_regex.match("Table 1: Results")
        assert matcher.caption_regex.match("TABLE 2. Data")

    def test_matches_roman_numeral(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        assert matcher.caption_regex.match("Table I: Introduction")
        assert matcher.caption_regex.match("Table IV: Methods")

    def test_no_match(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        assert not matcher.caption_regex.match("Figure 1: Test")
        assert not matcher.caption_regex.match("Just some text")


class TestProcess:
    def test_no_tables(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        doc = MagicMock()
        doc.blocks = [_mkblock("Text")]
        doc.tables = []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = matcher.process(doc)
        assert result is doc

    def test_no_blocks(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        doc = MagicMock()
        doc.blocks = []
        doc.tables = [MagicMock()]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = matcher.process(doc)
        assert result is doc

    def test_matches_caption_to_table(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        doc = MagicMock()
        doc.blocks = [
            _mkblock("Table 1: Results", BlockType.BODY, 0, "cap1"),
            _mkblock("Data row", BlockType.BODY, 1, "b2"),
        ]
        tbl = MagicMock()
        tbl.block_index = 1
        tbl.table_id = "tbl_001"
        tbl.caption_text = None
        doc.tables = [tbl]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1: Results"
        assert result.tables[0].caption_block_id == "cap1"

    def test_caption_after_table(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        doc = MagicMock()
        doc.blocks = [
            _mkblock("Data row", BlockType.BODY, 0, "b1"),
            _mkblock("Table 1: Results", BlockType.BODY, 1, "cap1"),
        ]
        tbl = MagicMock()
        tbl.block_index = 0
        tbl.table_id = "tbl_001"
        tbl.caption_text = None
        doc.tables = [tbl]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = matcher.process(doc)
        assert result.tables[0].caption_text == "Table 1: Results"

    def test_missing_caption_marked(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        doc = MagicMock()
        doc.blocks = [
            _mkblock("Some text", BlockType.BODY, 0, "b1"),
        ]
        tbl = MagicMock()
        tbl.block_index = 0
        tbl.table_id = "tbl_001"
        tbl.caption_text = None
        tbl.metadata = {}
        doc.tables = [tbl]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = matcher.process(doc)
        assert result.tables[0].metadata.get("caption_status") == "Missing"

    def test_exception_handling(self):
        from app.pipeline.tables.caption_matcher import TableCaptionMatcher
        matcher = TableCaptionMatcher()
        doc = MagicMock()
        doc.blocks = [_mkblock("Text")]
        doc.tables = [MagicMock()]
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None
        doc.tables[0].block_index = 999

        result = matcher.process(doc)
        assert result is doc


class TestMatchTableCaptionsConvenience:
    def test_convenience_function(self):
        from app.pipeline.tables.caption_matcher import match_table_captions
        doc = MagicMock()
        doc.blocks = []
        doc.tables = []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None

        result = match_table_captions(doc)
        assert result is doc
