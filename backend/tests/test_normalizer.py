from unittest.mock import MagicMock


class TestCalculateMedianFontSize:
    def test_returns_median(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        blocks = []
        for size in [10, 12, 14]:
            b = MagicMock()
            b.style.font_size = size
            b.text.strip.return_value = "text"
            blocks.append(b)
        assert n._calculate_median_font_size(blocks) == 12.0

    def test_returns_none_for_empty(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._calculate_median_font_size([]) is None

    def test_skips_empty_text_blocks(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.style.font_size = 14
        b.text.strip.return_value = ""
        assert n._calculate_median_font_size([b]) is None


class TestRepairCommonCorruptions:
    def test_fixes_number_word_merges(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        cases = {
            "2ethodology": "2 Methodology",
            "1ntroduction": "1 Introduction",
            "3esults": "3 Results",
            "4iscussion": "4 Discussion",
            "5onclusion": "5 Conclusion",
            "6eferences": "6 References",
            "7bstract": "7 Abstract",
        }
        for inp, expected in cases.items():
            assert n._repair_common_corruptions(inp) == expected

    def test_passes_clean_text(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("Introduction") == "Introduction"

    def test_empty_string(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        assert n._repair_common_corruptions("") == ""


class TestSanitizeEmptyOrphanBlocks:
    def test_removes_empty_body_block(self):
        from app.pipeline.normalization.normalizer import Normalizer
        from app.models.block import BlockType
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = ""
        b.block_type = BlockType.BODY
        b.metadata = {}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 0

    def test_keeps_block_with_figure(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = ""
        b.block_type = "UNKNOWN"
        b.metadata = {"has_figure": True}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_keeps_non_empty_block(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = "real content"
        b.block_type = "BODY"
        b.metadata = {}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_keeps_block_with_list_level(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = ""
        b.block_type = "BODY"
        b.metadata = {"list_level": 1}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_keeps_block_with_anchor_flag(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = ""
        b.block_type = "BODY"
        b.metadata = {"figure_anchor": True}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_keeps_heading_blocks(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = ""
        b.block_type = "HEADING"
        b.metadata = {}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1

    def test_keeps_equation_block(self):
        from app.pipeline.normalization.normalizer import Normalizer
        n = Normalizer()
        b = MagicMock()
        b.text.strip.return_value = ""
        b.block_type = "BODY"
        b.metadata = {"has_equation": True}
        result = n._sanitize_empty_orphan_blocks([b])
        assert len(result) == 1
