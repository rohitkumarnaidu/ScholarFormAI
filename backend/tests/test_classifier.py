from unittest.mock import MagicMock, patch


class TestLooksLikeHeading:
    def test_heading_candidate_metadata(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "Some text"
        block.metadata = {"is_heading_candidate": True}
        assert cc._looks_like_heading(block)

    def test_all_caps_short_text(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "INTRODUCTION"
        block.metadata = {}
        assert cc._looks_like_heading(block)

    def test_title_case_short_text(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "Related Work"
        block.metadata = {}
        assert cc._looks_like_heading(block)

    def text_ending_with_colon(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "Methods:"
        block.metadata = {}
        assert cc._looks_like_heading(block)

    def test_long_text_not_heading(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "This is a very long paragraph that clearly is not a heading " * 5
        block.metadata = {}
        assert not cc._looks_like_heading(block)


class TestResolveHeadingType:
    def test_level_2(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.metadata = {"level": 2}
        block.level = 2
        result, name = cc._resolve_heading_type(block)
        assert result == BlockType.HEADING_2

    def test_default_level_1(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.metadata = {}
        block.level = None
        result, name = cc._resolve_heading_type(block)
        assert result == BlockType.HEADING_1


class TestMapScibertLabel:
    def test_title_mapping(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "My Paper"
        result, name = cc._map_scibert_label("TITLE", block)
        assert result == BlockType.TITLE

    def test_abstract_heading(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "Abstract"
        result, name = cc._map_scibert_label("ABSTRACT", block)
        assert result == BlockType.ABSTRACT_HEADING

    def test_abstract_body(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.text = "This paper discusses..."
        block.metadata = {}
        result, name = cc._map_scibert_label("ABSTRACT", block)
        assert result == BlockType.ABSTRACT_BODY


class TestIsLikelyAffiliation:
    def test_university_keyword(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert cc._is_likely_affiliation("University of Cambridge")

    def test_no_match(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert not cc._is_likely_affiliation("John Smith")


class TestFindFirstSectionIndex:
    def test_finds_heading_candidate(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b1 = MagicMock()
        b1.text = "John Smith"
        b1.metadata = {}
        b1.block_type = "TITLE"
        b2 = MagicMock()
        b2.text = "Introduction"
        b2.metadata = {"is_heading_candidate": True}
        b2.block_type = "HEADING_1"
        idx = cc._find_first_section_index([b1, b2])
        assert idx == 1

    def test_finds_fallback_keyword(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.text = "Introduction"
        b.metadata = {}
        idx = cc._find_first_section_index([b])
        assert idx == 0

    def test_limits_front_matter_to_30(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        blocks = [MagicMock(text="Block", metadata={}) for _ in range(35)]
        idx = cc._find_first_section_index(blocks)
        assert idx <= 12

    def test_breaks_on_long_text(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.text = "X" * 400
        b.metadata = {}
        idx = cc._find_first_section_index([b])
        assert idx == 1


class TestFindReferencesStartIndex:
    def test_finds_references_heading(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.text = "References"
        b.metadata = {"is_heading_candidate": True}
        b.section_name = "References"
        idx = cc._find_references_start_index([b])
        assert idx == 0

    def test_skips_non_heading(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.text = "References"
        b.metadata = {}
        idx = cc._find_references_start_index([b])
        assert idx is None

    def test_skips_long_text(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        b = MagicMock()
        b.text = "See references for more info on this topic"
        b.metadata = {"is_heading_candidate": True}
        b.section_name = ""
        idx = cc._find_references_start_index([b])
        assert idx is not None


class TestMatchGrobidAuthor:
    def test_full_name_match(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert cc._match_grobid_author("John Smith", [{"full_name": "John Smith", "given": "John", "family": "Smith"}])

    def test_no_match(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert not cc._match_grobid_author("Unknown Text", [{"full_name": "John Smith"}])

    def test_family_name_match(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert cc._match_grobid_author("Smith", [{"full_name": "", "given": "John", "family": "Smith"}])


class TestMatchGrobidAffiliation:
    def test_full_match(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert cc._match_grobid_affiliation("MIT", ["MIT"])

    def test_no_match(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        assert not cc._match_grobid_affiliation("Google", ["MIT"])


class TestNlpClassifyFallback:
    def test_footnote_detected(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.block_type = BlockType.UNKNOWN
        block.text = "1 This is a footnote"
        block.metadata = {}
        cc._nlp_classify_fallback([block])
        assert block.block_type == BlockType.FOOTNOTE

    def test_equation_detected(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.block_type = BlockType.UNKNOWN
        block.text = "x = \\sum_{i=1}^n"
        block.metadata = {}
        cc._nlp_classify_fallback([block])
        assert block.block_type == BlockType.EQUATION

    def test_already_classified_skipped(self):
        from app.models import BlockType
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        block = MagicMock()
        block.block_type = BlockType.TITLE
        block.text = "Something"
        block.metadata = {}
        cc._nlp_classify_fallback([block])
        assert block.block_type == BlockType.TITLE


class TestProcess:
    def test_empty_blocks_returns_doc(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        doc = MagicMock()
        doc.blocks = []
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None
        result = cc.process(doc)
        assert result is doc

    def test_exception_handled(self):
        from app.pipeline.classification.classifier import ContentClassifier
        cc = ContentClassifier()
        doc = MagicMock()
        doc.blocks = [MagicMock()]
        doc.blocks[0].text = "Hello"
        doc.blocks[0].metadata = {}
        doc.blocks[0].block_type = "UNKNOWN"
        doc.add_processing_stage = MagicMock()
        doc.updated_at = None
        doc.metadata.ai_hints = None
        result = cc.process(doc)
        assert result is doc


class TestConvenienceFunction:
    def test_classify_content(self):
        from app.pipeline.classification.classifier import classify_content
        with patch("app.pipeline.classification.classifier.ContentClassifier.process") as mock_proc:
            doc = MagicMock()
            mock_proc.return_value = doc
            result = classify_content(doc)
            assert result is doc
