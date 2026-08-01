# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.pipeline.formatting.style_mapper import StyleMapper


@pytest.fixture
def mock_contract_loader():

    loader = MagicMock()
    loader.load.return_value = {
        "styles": {
            "BLOCK_HEADING_1": "Heading 1",
            "BLOCK_BODY": "Normal",
            "BLOCK_FIGURE_CAPTION": "Caption",
        }
    }
    return loader

class TestStyleMapper:
    def test_heading_1_style(self, mock_contract_loader):
        from app.models import Block, BlockType
        mapper = StyleMapper(mock_contract_loader)
        block = Block(block_id="b1", text="Intro", index=1, block_type=BlockType.HEADING_1)
        style = mapper.get_style_name(block, "ieee")
        assert style == "Heading 1"

    def test_body_style(self, mock_contract_loader):
        from app.models import Block, BlockType
        mapper = StyleMapper(mock_contract_loader)
        block = Block(block_id="b1", text="Body text", index=1, block_type=BlockType.BODY)
        style = mapper.get_style_name(block, "ieee")
        assert style == "Normal"

    def test_figure_caption_style(self, mock_contract_loader):
        from app.models import Block, BlockType
        mapper = StyleMapper(mock_contract_loader)
        block = Block(block_id="b1", text="Fig 1.", index=1, block_type=BlockType.FIGURE_CAPTION)
        style = mapper.get_style_name(block, "ieee")
        assert style == "Caption"

    def test_missing_style_returns_normal(self, mock_contract_loader):
        from app.models import Block, BlockType
        mapper = StyleMapper(mock_contract_loader)
        block = Block(block_id="b1", text="Equation", index=1, block_type=BlockType.EQUATION)
        style = mapper.get_style_name(block, "ieee")
        assert style == "Normal"

    def test_block_type_already_prefixed(self, mock_contract_loader):
        from app.models import Block, BlockType
        mapper = StyleMapper(mock_contract_loader)
        block = Block(block_id="b1", text="Intro", index=1, block_type=BlockType.HEADING_1)
        # by default block_type is e.g. HEADING_1, so bt = "heading_1"
        style = mapper.get_style_name(block, "ieee")
        assert style == "Heading 1"

    def test_different_publisher(self, mock_contract_loader):
        from app.models import Block, BlockType
        loader = MagicMock()
        loader.load.return_value = {
            "styles": {
                "BLOCK_HEADING_1": "APA Heading 1",
            }
        }
        mapper = StyleMapper(loader)
        block = Block(block_id="b1", text="Intro", index=1, block_type=BlockType.HEADING_1)
        style = mapper.get_style_name(block, "apa")
        assert style == "APA Heading 1"
