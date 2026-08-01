# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations
from unittest.mock import patch, MagicMock
import pytest
pytestmark = [pytest.mark.pipeline]


@pytest.fixture
def detector():
    with patch("app.pipeline.structure_detection.detector.ContractLoader") as mock_cl, \
         patch("app.pipeline.structure_detection.detector.safe_execution") as mock_se, \
         patch("app.pipeline.structure_detection.detector.safe_function") as mock_sf:
        ctx_mgr = MagicMock()
        ctx_mgr.__enter__.return_value = None
        ctx_mgr.__exit__.return_value = None
        mock_se.return_value = ctx_mgr
        mock_sf.return_value = lambda f: f
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector(contracts_dir="/fake/contracts")
        det.avg_font_size = 12.0
        yield det


@pytest.fixture
def doc_with_blocks():
    from app.models import PipelineDocument as Document
    from app.models import DocumentMetadata, TemplateInfo
    blocks_list = [
        _b("My Research Paper", index=0, bid="b0"),
        _b("John Smith", index=1, bid="b1"),
        _b("University of Science", index=2, bid="b2"),
        _b("Abstract", index=3, bid="b3"),
        _b("This is the abstract content.", index=4, bid="b4"),
        _b("1. Introduction", index=5, bid="b5"),
        _b("This is the introduction body.", index=6, bid="b6"),
        _b("2. Methods", index=7, bid="b7"),
        _b("Methods description.", index=8, bid="b8"),
    ]
    meta = DocumentMetadata()
    return Document(document_id="test_doc", blocks=blocks_list, metadata=meta, template=TemplateInfo(template_name="IEEE"))


def _b(text: str, index: int = 0, bid: str | None = None, font_size: float = 12.0, bold: bool = False):
    from app.models import Block, BlockType
    from app.models import TextStyle
    style = TextStyle(font_size=font_size, bold=bold)
    return Block(block_id=bid or f"b{index}", text=text, index=index, block_type=BlockType.UNKNOWN, style=style, metadata={})


class TestCalculateAvgFontSize:
    def test_with_font_sizes(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        blocks = [
            _b("Title", font_size=18.0),
            _b("Body", font_size=12.0),
            _b("Body2", font_size=12.0),
        ]
        result = det._calculate_avg_font_size(blocks)
        assert result == 12.0

    def test_no_font_sizes(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        from app.models import Block, BlockType, TextStyle
        det = StructureDetector.__new__(StructureDetector)
        blocks = [
            Block(block_id="b0", text="Text", index=0, block_type=BlockType.UNKNOWN, style=TextStyle(font_size=None), metadata={}),
            Block(block_id="b1", text="", index=1, block_type=BlockType.UNKNOWN, style=TextStyle(font_size=None), metadata={}),
        ]
        result = det._calculate_avg_font_size(blocks)
        assert result is None

    def test_only_empty_text_blocks(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        blocks = [_b("", font_size=12.0), _b("", font_size=14.0)]
        result = det._calculate_avg_font_size(blocks)
        assert result is None


class TestDetectHeadingCandidates:
    def test_title_detected_first_block(self, detector):
        blocks = [_b("My Paper", index=0), _b("Body text", index=1)]
        result = detector._detect_heading_candidates(blocks)
        assert len(result) >= 1
        assert result[0]["level"] == 0

    def test_header_footer_skipped(self, detector):
        from app.models import Block, BlockType
        blocks = [
            Block(block_id="hdr", index=0, text="Header", block_type=BlockType.UNKNOWN, metadata={"is_header": True}),
            _b("Real Title", index=1),
            _b("1. Introduction", index=2),
        ]
        result = detector._detect_heading_candidates(blocks)
        assert len(result) >= 1
        assert not any("Header" in c["block"].text for c in result)

    def test_empty_block_skipped(self, detector):
        blocks = [_b("", index=0), _b("Title", index=1)]
        result = detector._detect_heading_candidates(blocks)
        assert len(result) == 1
        assert result[0]["block"].text == "Title"

    def test_title_with_author_detection(self, detector):
        blocks = [
            _b("Paper Title", index=0),
            _b("John Smith", index=1),
            _b("University of Science", index=2),
            _b("1. Introduction", index=3),
        ]
        result = detector._detect_heading_candidates(blocks)
        assert blocks[1].metadata.get("is_author_block") is True
        assert blocks[2].metadata.get("is_affiliation_block") is True

    def test_author_lookup_stops_after_heading(self, detector):
        blocks = [
            _b("Paper Title", index=0),
            _b("1. Introduction", index=1),
            _b("John Smith", index=2),
        ]
        result = detector._detect_heading_candidates(blocks)
        assert blocks[2].metadata.get("is_author_block") is None

    def test_analysis_candidate_found(self, detector):
        blocks = [
            _b("Some Title", index=0),
            _b("1. Introduction", index=1),
            _b("Body text", index=2),
        ]
        result = detector._detect_heading_candidates(blocks)
        assert len(result) >= 1

    def test_numbering_info_stored(self, detector):
        blocks = [
            _b("Title", index=0),
            _b("1.1 Sub Section", index=1),
        ]
        result = detector._detect_heading_candidates(blocks)
        assert result[1]["block"].metadata.get("numbering_info") is not None


class TestAssignSectionNames:
    def test_assigns_section_names(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        blocks = [_b("Intro", index=0, bid="b0"), _b("Body", index=1, bid="b1")]
        headings = [{"block_id": "b0", "level": 1, "block": blocks[0]}]
        det._assign_section_names(blocks, headings)
        assert blocks[0].section_name == "Intro"
        assert blocks[1].section_name == "Intro"

    def test_title_section_name(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import BlockType
        blocks = [_b("Title", index=0, bid="b0")]
        blocks[0].block_type = BlockType.TITLE
        headings = [{"block_id": "b0", "level": 0, "block": blocks[0]}]
        det._assign_section_names(blocks, headings)
        assert blocks[0].section_name == "title"

    def test_header_footer_no_section(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import Block, BlockType
        blocks = [
            Block(block_id="hdr", index=0, text="Header", block_type=BlockType.UNKNOWN, metadata={"is_header": True}),
            _b("Intro", index=1, bid="b1"),
        ]
        headings = [{"block_id": "b1", "level": 1, "block": blocks[1]}]
        det._assign_section_names(blocks, headings)
        assert blocks[0].section_name is None

    def test_numbering_removed_from_section_name(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        blocks = [_b("1. Introduction", index=0, bid="b0")]
        headings = [{"block_id": "b0", "level": 1, "block": blocks[0]}]
        blocks[0].metadata["numbering_info"] = {"remainder": "Introduction"}
        det._assign_section_names(blocks, headings)
        assert "1." not in blocks[0].section_name

    def test_no_current_section_non_heading(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        blocks = [_b("Intro", index=0, bid="b0"), _b("Body", index=1, bid="b1")]
        det._assign_section_names(blocks, [])
        assert blocks[1].section_name is None


class TestBuildHierarchy:
    def test_parent_child_relationship(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        blocks = [
            _b("1. Intro", index=0, bid="b0"),
            _b("1.1 Sub", index=1, bid="b1"),
            _b("2. Methods", index=2, bid="b2"),
        ]
        headings = [
            {"block_id": "b0", "level": 1, "block": blocks[0]},
            {"block_id": "b1", "level": 2, "block": blocks[1]},
            {"block_id": "b2", "level": 1, "block": blocks[2]},
        ]
        det._build_hierarchy(blocks, headings)
        assert blocks[1].parent_id == "b0"
        assert blocks[2].parent_id is None

    def test_header_skipped(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import Block, BlockType
        blocks = [
            Block(block_id="hdr", index=0, text="H", block_type=BlockType.UNKNOWN, metadata={"is_header": True}),
            _b("Intro", index=1, bid="b1"),
        ]
        headings = [{"block_id": "b1", "level": 1, "block": blocks[1]}]
        det._build_hierarchy(blocks, headings)
        assert blocks[0].parent_id is None


class TestValidateHierarchy:
    def test_no_jump(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import Block, BlockType
        b1 = Block(block_id="b1", index=0, text="Intro", block_type=BlockType.HEADING_1, level=1)
        b2 = Block(block_id="b2", index=1, text="Sub", block_type=BlockType.HEADING_2, level=2)
        det._validate_hierarchy([b1, b2])
        assert b1.is_valid is not False

    def test_jump_detected(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import Block, BlockType
        b1 = Block(block_id="b1", index=0, text="Intro", block_type=BlockType.HEADING_1, level=1)
        b2 = Block(block_id="b2", index=1, text="Jump", block_type=BlockType.HEADING_3, level=3)
        det._validate_hierarchy([b1, b2])
        assert b2.is_valid is False

    def test_jump_from_zero(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import Block, BlockType
        b1 = Block(block_id="b2", index=0, text="Jump", block_type=BlockType.HEADING_2, level=2)
        det._validate_hierarchy([b1])
        assert b1.is_valid is False

    def test_header_skipped_in_validation(self):
        from app.pipeline.structure_detection.detector import StructureDetector
        det = StructureDetector.__new__(StructureDetector)
        from app.models import Block, BlockType
        hdr = Block(block_id="h", index=0, text="H", block_type=BlockType.BODY, metadata={"is_header": True})
        b1 = Block(block_id="b1", index=1, text="Intro", block_type=BlockType.HEADING_1, level=1)
        det._validate_hierarchy([hdr, b1])
        assert hdr.is_valid is True  # headers are skipped, not invalidated


class TestCanonicalizeSections:
    def test_canonicalize_success(self, detector):
        detector.contract_loader.get_canonical_name.return_value = "References"
        from app.models import Block, BlockType
        block = Block(block_id="b1", index=0, text="Bibliography", block_type=BlockType.HEADING_1, section_name="Bibliography")
        detector._canonicalize_sections([block], "IEEE")
        assert block.section_name == "References"

    def test_canonicalize_exception(self, detector):
        detector.contract_loader.get_canonical_name.side_effect = Exception("Fail")
        from app.models import Block, BlockType
        block = Block(block_id="b1", index=0, text="Intro", block_type=BlockType.HEADING_1, section_name="Introduction")
        detector._canonicalize_sections([block], "IEEE")
        assert block.section_name == "Introduction"

    def test_canonicalize_none_section(self, detector):
        from app.models import Block, BlockType
        block = Block(block_id="b1", index=0, text="NoSection", block_type=BlockType.BODY)
        detector._canonicalize_sections([block], "IEEE")
        detector.contract_loader.get_canonical_name.assert_not_called()


class TestDetectStructureWithDocling:
    def test_docling_empty_elements_fallback(self, detector):
        result = detector._detect_structure_with_docling([], {"elements": []})
        assert isinstance(result, list)

    def test_docling_normal_flow(self, detector):
        layout_data = {
            "elements": [
                {"text": "My Paper", "type": "title", "font_size": 24, "bbox": {"page": 1, "y0": 100}, "confidence": 0.95},
                {"text": "1. Introduction", "type": "section_header", "font_size": 16, "bbox": {"page": 1, "y0": 200}, "confidence": 0.9},
            ]
        }
        blocks = [
            _b("My Paper", index=0, bid="b0"),
            _b("1. Introduction", index=1, bid="b1"),
        ]
        result = detector._detect_structure_with_docling(blocks, layout_data)
        assert len(result) >= 1

    def test_docling_no_candidates_fallback(self, detector):
        layout_data = {
            "elements": [
                {"text": "Body text", "type": "paragraph", "font_size": 12, "bbox": {"page": 1, "y0": 300}},
            ]
        }
        blocks = [_b("Body text", index=0, bid="b0")]
        result = detector._detect_structure_with_docling(blocks, layout_data)
        assert isinstance(result, list)

    def test_docling_title_in_top_half(self, detector):
        layout_data = {
            "elements": [
                {"text": "Paper Title", "type": "title", "font_size": 20, "bbox": {"page": 1, "y0": 100}},
            ]
        }
        blocks = [_b("Paper Title", index=0, bid="b0")]
        result = detector._detect_structure_with_docling(blocks, layout_data)
        assert len(result) >= 1

    def test_docling_title_below_top_half_skipped(self, detector):
        layout_data = {
            "elements": [
                {"text": "Not Title", "type": "title", "font_size": 20, "bbox": {"page": 1, "y0": 600}},
                {"text": "Body", "type": "paragraph", "font_size": 12},
            ]
        }
        blocks = [_b("Not Title", index=0, bid="b0"), _b("Body", index=1, bid="b1")]
        result = detector._detect_structure_with_docling(blocks, layout_data)
        assert isinstance(result, list)

    def test_docling_heading_no_font_size(self, detector):
        layout_data = {
            "elements": [
                {"text": "Intro", "type": "section_header", "bbox": {"page": 1, "y0": 200}},
            ]
        }
        blocks = [_b("Intro", index=0, bid="b0")]
        result = detector._detect_structure_with_docling(blocks, layout_data)
        assert len(result) >= 1

    def test_docling_token_overlap_match(self, detector):
        layout_data = {
            "elements": [
                {"text": "Methods and Materials", "type": "section_header", "font_size": 16, "bbox": {"page": 1, "y0": 200}},
            ]
        }
        blocks = [_b("Methods Materials", index=0, bid="b0")]
        result = detector._detect_structure_with_docling(blocks, layout_data)
        assert isinstance(result, list)


class TestDetectStructureConvenience:
    def test_detect_structure_function(self):
        with patch("app.pipeline.structure_detection.detector.ContractLoader"), \
             patch("app.pipeline.structure_detection.detector.safe_execution") as mock_se, \
             patch("app.pipeline.structure_detection.detector.safe_function") as mock_sf:
            mock_se.return_value.__enter__ = MagicMock()
            mock_se.return_value.__exit__ = MagicMock()
            mock_sf.return_value = lambda f: f
            from app.pipeline.structure_detection.detector import detect_structure
            from app.models import PipelineDocument as Document
            doc = Document(document_id="test")
            result = detect_structure(doc)
            assert result is doc


class TestProcess:
    def test_process_full_pipeline(self, detector, doc_with_blocks):
        with patch("app.pipeline.normalization.normalizer.Normalizer") as mock_norm_cls:
            mock_norm = MagicMock()
            mock_norm.process.return_value = doc_with_blocks
            mock_norm_cls.return_value = mock_norm
            with patch.object(detector, "_calculate_avg_font_size", return_value=12.0), \
                 patch.object(detector, "_detect_heading_candidates", return_value=[]), \
                 patch.object(detector, "_assign_section_names"), \
                 patch.object(detector, "_build_hierarchy"), \
                 patch.object(detector, "_canonicalize_sections"), \
                 patch.object(detector, "_validate_hierarchy"), \
                 patch.object(detector, "process", wraps=detector.process) as mock_process:
                result = detector.process(doc_with_blocks)
                assert result is doc_with_blocks
                assert "structure_detection" in [s.stage_name for s in result.processing_history]

    def test_process_with_docling_layout(self, detector, doc_with_blocks):
        doc_with_blocks.metadata.ai_hints["docling_layout"] = {
            "elements": [{"text": "Title", "type": "title", "font_size": 20}]
        }
        with patch("app.pipeline.normalization.normalizer.Normalizer") as mock_norm_cls:
            mock_norm = MagicMock()
            mock_norm.process.return_value = doc_with_blocks
            mock_norm_cls.return_value = mock_norm
            with patch.object(detector, "_calculate_avg_font_size", return_value=12.0), \
                 patch.object(detector, "_detect_structure_with_docling", return_value=[]), \
                 patch.object(detector, "_detect_heading_candidates", return_value=[]), \
                 patch.object(detector, "_assign_section_names"), \
                 patch.object(detector, "_build_hierarchy"), \
                 patch.object(detector, "_canonicalize_sections"), \
                 patch.object(detector, "_validate_hierarchy"):
                result = detector.process(doc_with_blocks)
                assert result is doc_with_blocks

    def test_process_docling_fails_fallback(self, detector, doc_with_blocks):
        doc_with_blocks.metadata.ai_hints["docling_layout"] = {
            "elements": [{"text": "Title", "type": "title", "font_size": 20}]
        }
        with patch("app.pipeline.normalization.normalizer.Normalizer") as mock_norm_cls:
            mock_norm = MagicMock()
            mock_norm.process.return_value = doc_with_blocks
            mock_norm_cls.return_value = mock_norm
            with patch.object(detector, "_calculate_avg_font_size", return_value=12.0), \
                 patch.object(detector, "_detect_structure_with_docling", return_value=[]), \
                 patch.object(detector, "_detect_heading_candidates", return_value=[]), \
                 patch.object(detector, "_assign_section_names"), \
                 patch.object(detector, "_build_hierarchy"), \
                 patch.object(detector, "_canonicalize_sections"), \
                 patch.object(detector, "_validate_hierarchy"):
                result = detector.process(doc_with_blocks)
                assert result is doc_with_blocks
