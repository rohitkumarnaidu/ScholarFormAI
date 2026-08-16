from unittest.mock import MagicMock


class TestConstructor:
    def test_sets_defaults(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        assert detector.avg_font_size is None
        assert detector.detected_headings == []
        assert detector.contract_loader is not None


class TestCalculateAvgFontSize:
    def test_returns_median(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        b1 = MagicMock()
        b1.style.font_size = 12.0
        b1.text = "Hello"
        b2 = MagicMock()
        b2.style.font_size = 14.0
        b2.text = "World"
        b3 = MagicMock()
        b3.style.font_size = 16.0
        b3.text = "Foo"
        result = detector._calculate_avg_font_size([b1, b2, b3])
        assert result == 14.0

    def test_returns_none_when_no_font_sizes(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        b = MagicMock()
        b.style.font_size = None
        b.text = "Hello"
        result = detector._calculate_avg_font_size([b])
        assert result is None

    def test_skips_empty_text(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        b = MagicMock()
        b.style.font_size = 12.0
        b.text = ""
        result = detector._calculate_avg_font_size([b])
        assert result is None


class TestValidateHierarchy:
    def test_no_jump_if_sequential(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        b1 = MagicMock()
        b1.metadata = {}
        b1.is_heading.return_value = True
        b1.level = 1
        b1.warnings = []
        b1.is_valid = True
        b2 = MagicMock()
        b2.metadata = {}
        b2.is_heading.return_value = True
        b2.level = 2
        b2.warnings = []
        b2.is_valid = True
        detector._validate_hierarchy([b1, b2])
        assert b2.is_valid is True

    def test_detects_jump(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        b1 = MagicMock()
        b1.metadata = {}
        b1.is_heading.return_value = True
        b1.level = 1
        b1.warnings = []
        b1.is_valid = True
        b2 = MagicMock()
        b2.metadata = {}
        b2.is_heading.return_value = True
        b2.level = 3
        b2.warnings = []
        b2.is_valid = True
        detector._validate_hierarchy([b1, b2])
        assert len(b2.warnings) > 0
        assert b2.is_valid is False

    def test_skips_header_footer(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        b = MagicMock()
        b.metadata = {"is_header": True}
        b.is_heading.return_value = True
        b.level = 3
        b.warnings = []
        b.is_valid = True
        detector._validate_hierarchy([b])
        assert b.is_valid is True


class TestBuildHierarchy:
    def test_parent_assignment(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        h1 = {"block_id": "b1", "level": 1}
        h2 = {"block_id": "b2", "level": 2}
        b1 = MagicMock()
        b1.block_id = "b1"
        b1.metadata = {}
        b1.parent_id = None
        b2 = MagicMock()
        b2.block_id = "b2"
        b2.metadata = {}
        b2.parent_id = None
        detector._build_hierarchy([b1, b2], [h1, h2])
        assert b2.parent_id == "b1"

    def test_no_parent_for_level_1(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        h1 = {"block_id": "b1", "level": 1}
        b1 = MagicMock()
        b1.block_id = "b1"
        b1.metadata = {}
        b1.parent_id = None
        detector._build_hierarchy([b1], [h1])
        assert b1.parent_id is None

    def test_skips_header_footer(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        h1 = {"block_id": "b1", "level": 1}
        b1 = MagicMock()
        b1.block_id = "b1"
        b1.metadata = {"is_header": True}
        b1.parent_id = None
        detector._build_hierarchy([b1], [h1])
        assert b1.parent_id is None


class TestAssignSectionNames:
    def test_section_inheritance(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        h = MagicMock()
        h.block_id = "h1"
        h.text = "Intro"
        h.block_type = "HEADING_1"
        h.metadata = {}
        h.section_name = None
        b = MagicMock()
        b.block_id = "b2"
        b.text = "Body"
        b.block_type = "BODY"
        b.metadata = {}
        b.section_name = None
        heading_candidates = [{"block_id": "h1", "level": 1, "block": h}]
        detector._assign_section_names([h, b], heading_candidates)
        assert h.section_name == "Intro"
        assert b.section_name == "Intro"

    def test_title_level_0(self):
        from app.pipeline.structure_detection.detector import StructureDetector

        detector = StructureDetector(contracts_dir="/tmp")
        h = MagicMock()
        h.block_id = "h1"
        h.text = "My Paper"
        h.block_type = "TITLE"
        h.metadata = {}
        h.section_name = None
        heading_candidates = [{"block_id": "h1", "level": 0, "block": h}]
        detector._assign_section_names([h], heading_candidates)
        assert h.section_name == "title"
