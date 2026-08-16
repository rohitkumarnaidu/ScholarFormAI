from __future__ import annotations


class TestBlock:
    def test_block_type_enum_values(self):
        from app.models.block import BlockType

        assert BlockType.TITLE.value == "title"
        assert BlockType.BODY.value == "body"
        assert BlockType.HEADING_1.value == "heading_1"
        assert BlockType.FIGURE_CAPTION.value == "figure_caption"
        assert BlockType.UNKNOWN.value == "unknown"

    def test_list_type_enum(self):
        from app.models.block import ListType

        assert ListType.ORDERED.value == "ordered"
        assert ListType.UNORDERED.value == "unordered"

    def test_text_style_defaults(self):
        from app.models.block import TextStyle

        ts = TextStyle()
        assert ts.bold is False
        assert ts.italic is False
        assert ts.font_name is None

    def test_text_style_frozen(self):
        from app.models.block import TextStyle

        ts = TextStyle(bold=True, font_name="Arial")
        assert ts.bold is True
        assert ts.font_name == "Arial"

    def test_block_create(self):
        from app.models.block import Block, BlockType, TextStyle

        b = Block(block_id="b1", text="Hello", index=0, block_type=BlockType.BODY)
        assert b.block_id == "b1"
        assert b.text == "Hello"
        assert b.index == 0
        assert b.block_type == BlockType.BODY
        assert isinstance(b.style, TextStyle)

    def test_block_defaults(self):
        from app.models.block import Block

        b = Block(block_id="b2", text="Test", index=1)
        assert b.block_type.value == "unknown"
        assert b.is_valid is True
        assert b.warnings == []
        assert b.metadata == {}

    def test_block_is_heading(self):
        from app.models.block import Block, BlockType

        h = Block(block_id="h1", text="Intro", index=0, block_type=BlockType.HEADING_1)
        assert h.is_heading() is True
        b = Block(block_id="b1", text="Body", index=1, block_type=BlockType.BODY)
        assert b.is_heading() is False

    def test_block_is_content(self):
        from app.models.block import Block, BlockType

        p = Block(block_id="p1", text="Para", index=0, block_type=BlockType.PARAGRAPH)
        assert p.is_content() is True
        t = Block(block_id="t1", text="Title", index=1, block_type=BlockType.TITLE)
        assert t.is_content() is False

    def test_block_is_metadata(self):
        from app.models.block import Block, BlockType

        t = Block(block_id="t1", text="Title", index=0, block_type=BlockType.TITLE)
        assert t.is_metadata() is True
        b = Block(block_id="b1", text="Body", index=1, block_type=BlockType.BODY)
        assert b.is_metadata() is False

    def test_block_with_all_fields(self):
        from app.models.block import Block, BlockType, ListType

        b = Block(
            block_id="b1",
            text="Item",
            index=0,
            block_type=BlockType.LIST_ITEM,
            page_number=3,
            level=1,
            parent_id="parent1",
            list_type=ListType.ORDERED,
            list_level=0,
            section_name="Methods",
            semantic_intent="METHODS_BODY",
            classification_confidence=0.95,
            contains_citation=True,
            citation_keys=["Smith2020"],
            is_valid=False,
            warnings=["Too short"],
            metadata={"source": "pdf"},
        )
        assert b.page_number == 3
        assert b.level == 1
        assert b.list_type == ListType.ORDERED
        assert b.section_name == "Methods"
        assert b.classification_confidence == 0.95
        assert b.citation_keys == ["Smith2020"]

    def test_block_use_enum_values(self):
        from app.models.block import Block, BlockType

        b = Block(block_id="b1", text="Test", index=0, block_type="body")
        assert b.block_type == BlockType.BODY
