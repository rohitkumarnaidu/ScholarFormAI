from unittest.mock import MagicMock


class TestStyleMapper:
    def test_known_style(self):
        from app.pipeline.formatting.style_mapper import StyleMapper

        loader = MagicMock()
        loader.load.return_value = {"styles": {"BLOCK_HEADING_1": "Heading1"}}
        mapper = StyleMapper(loader)

        block = MagicMock()
        block.block_type = "heading_1"
        assert mapper.get_style_name(block, "ieee") == "Heading1"

    def test_missing_style_defaults_to_normal(self):
        from app.pipeline.formatting.style_mapper import StyleMapper

        loader = MagicMock()
        loader.load.return_value = {"styles": {}}
        mapper = StyleMapper(loader)

        block = MagicMock()
        block.block_type = "paragraph"
        assert mapper.get_style_name(block, "ieee") == "Normal"

    def test_already_prefixed_key(self):
        from app.pipeline.formatting.style_mapper import StyleMapper

        loader = MagicMock()
        loader.load.return_value = {"styles": {"BLOCK_PARAGRAPH": "BodyText"}}
        mapper = StyleMapper(loader)

        block = MagicMock()
        block.block_type = "BLOCK_PARAGRAPH"
        assert mapper.get_style_name(block, "ieee") == "BodyText"

    def test_contract_loaded_with_publisher(self):
        from app.pipeline.formatting.style_mapper import StyleMapper

        loader = MagicMock()
        mapper = StyleMapper(loader)
        block = MagicMock()
        block.block_type = "heading_1"

        mapper.get_style_name(block, "acm")
        loader.load.assert_called_once_with("acm")
