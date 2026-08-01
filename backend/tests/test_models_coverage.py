# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for ORM models: api_key, api_key_usage_log, block, figure, table, reference.
"""
from __future__ import annotations

import uuid

from app.models.api_key import UserApiKey
from app.models.api_key_usage_log import ApiKeyUsageLog
from app.models.block import Block, BlockType, ListType, TextStyle
from app.models.equation import Equation
from app.models.figure import Figure, FigureType, ImageFormat
from app.models.reference import Reference, ReferenceType
from app.models.table import Table, TableCell


class TestUserApiKeyModel:
    """Tests for UserApiKey model."""

    def test_to_dict_masks_key(self):
        key = UserApiKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            provider="openai",
            api_key_encrypted="encrypted-sk-1234567890abcdef",
            key_label="My Key",
            is_active=True,
            rate_limit_per_minute=60,
            rate_limit_per_hour=1000,
            daily_quota=10000,
            total_requests=42,
        )
        d = key.to_dict(mask_key=True)
        assert d["provider"] == "openai"
        assert d["key_label"] == "My Key"
        assert d["is_active"] is True
        assert d["total_requests"] == 42
        assert "..." in d["key_preview"]

    def test_to_dict_short_key(self):
        key = UserApiKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            provider="openai",
            api_key_encrypted="short",
        )
        d = key.to_dict(mask_key=True)
        assert d["key_preview"] == "****"

    def test_to_dict_no_mask(self):
        key = UserApiKey(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            provider="openai",
            api_key_encrypted="encrypted-value",
        )
        d = key.to_dict(mask_key=False)
        assert d["key_preview"] == "encrypted-value"


class TestApiKeyUsageLogModel:
    """Tests for ApiKeyUsageLog model."""

    def test_create_usage_log(self):
        log = ApiKeyUsageLog(
            user_api_key_id=uuid.uuid4(),
            endpoint="/api/v1/chat/completions",
            model="gpt-4",
            tokens_used=150,
            status_code=200,
            response_time_ms=350,
        )
        assert log.endpoint == "/api/v1/chat/completions"
        assert log.model == "gpt-4"
        assert log.tokens_used == 150
        assert log.status_code == 200


class TestBlockModel:
    """Tests for Block model."""

    def test_create_block(self):
        block = Block(
            block_id="blk-001",
            text="Hello world",
            block_type=BlockType.BODY,
            index=0,
        )
        assert block.block_id == "blk-001"
        assert block.text == "Hello world"
        assert block.block_type == BlockType.BODY
        assert block.index == 0

    def test_block_with_style(self):
        style = TextStyle(bold=True, italic=False, font_name="Arial", font_size=12)
        block = Block(
            block_id="blk-002",
            text="Styled text",
            block_type=BlockType.HEADING_1,
            index=1,
            style=style,
        )
        assert block.style.bold is True
        assert block.style.font_name == "Arial"

    def test_block_with_list(self):
        block = Block(
            block_id="blk-003",
            text="List item",
            block_type=BlockType.LIST_ITEM,
            index=2,
            list_type=ListType.ORDERED,
            list_level=1,
        )
        assert block.list_type == ListType.ORDERED
        assert block.list_level == 1

    def test_block_type_enum(self):
        assert BlockType.BODY.value == "body"
        assert BlockType.HEADING_1.value == "heading_1"
        assert BlockType.HEADING_2.value == "heading_2"
        assert BlockType.LIST_ITEM.value == "list_item"


class TestFigureModel:
    """Tests for Figure model."""

    def test_create_figure(self):
        fig = Figure(
            figure_id="fig-001",
            index=0,
            caption_text="Test figure",
            figure_type=FigureType.DIAGRAM,
            image_format=ImageFormat.PNG,
        )
        assert fig.figure_id == "fig-001"
        assert fig.caption_text == "Test figure"
        assert fig.figure_type == FigureType.DIAGRAM

    def test_figure_type_enum(self):
        assert FigureType.DIAGRAM.value == "diagram"
        assert FigureType.CHART.value == "chart"
        assert FigureType.GRAPH.value == "graph"


class TestTableModel:
    """Tests for Table model."""

    def test_create_table(self):
        cells = [
            TableCell(text="Header 1", row=0, col=0, is_header=True),
            TableCell(text="Header 2", row=0, col=1, is_header=True),
            TableCell(text="Data 1", row=1, col=0, is_header=False),
        ]
        table = Table(table_id="tbl-001", caption_text="Test table", cells=cells, num_rows=2, num_cols=2, index=0, block_index=0)
        assert table.table_id == "tbl-001"
        assert len(table.cells) == 3
        assert table.cells[0].is_header is True

    def test_table_cell(self):
        cell = TableCell(text="Cell content", row=2, col=3, is_header=False)
        assert cell.text == "Cell content"
        assert cell.row == 2
        assert cell.col == 3


class TestReferenceModel:
    """Tests for Reference model."""

    def test_create_reference(self):
        ref = Reference(
            reference_id="ref-001",
            raw_text="Smith, J. (2024). Test paper. Journal, 1(2), 100-110.",
            reference_type=ReferenceType.JOURNAL_ARTICLE,
            citation_key="smith2024",
            index=0,
        )
        assert ref.reference_id == "ref-001"
        assert ref.reference_type == ReferenceType.JOURNAL_ARTICLE

    def test_reference_type_enum(self):
        assert ReferenceType.JOURNAL_ARTICLE.value == "journal_article"
        assert ReferenceType.BOOK.value == "book"
        assert ReferenceType.CONFERENCE_PAPER.value == "conference_paper"


class TestEquationModel:
    """Tests for Equation model."""

    def test_create_equation(self):
        eq = Equation(
            equation_id="eq-001",
            mathml="<math><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></math>",
            text="E equals m c squared",
            index=0,
        )
        assert eq.equation_id == "eq-001"
        assert eq.text == "E equals m c squared"
