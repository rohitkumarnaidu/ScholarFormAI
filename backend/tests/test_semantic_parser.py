# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
SciBERT Semantic Parser Tests
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models import Block, BlockType
from app.pipeline.intelligence.semantic_parser import SemanticParser, get_semantic_parser


def _sample_blocks() -> list[Block]:
    return [
        Block(block_id="b-1", index=0, block_type=BlockType.BODY, text="Abstract of the manuscript."),
        Block(block_id="b-2", index=1, block_type=BlockType.BODY, text="Methods and experiments."),
        Block(block_id="b-3", index=2, block_type=BlockType.BODY, text="Conclusions and future work."),
    ]


class TestSemanticParser:
    @pytest.mark.unit
    def test_parser_initialization(self):
        parser = SemanticParser()
        assert parser is not None

    @pytest.mark.unit
    def test_model_loading(self):
        with patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer") as mock_tokenizer:
            with patch("app.pipeline.intelligence.semantic_parser.AutoModel") as mock_model:
                parser = SemanticParser()
                # CI can configure remote SciBERT URLs; force this test to
                # exercise the local-model load branch deterministically.
                parser.remote_base_urls = []
                parser._last_good_remote_url = None
                parser._load_model()
                assert parser.tokenizer is not None
                assert parser.model is not None
                assert mock_tokenizer.from_pretrained.called
                assert mock_model.from_pretrained.called

    @pytest.mark.unit
    def test_singleton_pattern(self):
        parser1 = get_semantic_parser()
        parser2 = get_semantic_parser()
        assert parser1 is parser2

    @pytest.mark.unit
    def test_analyze_blocks_uses_single_batch_inference_call(self):
        parser = SemanticParser()
        blocks = _sample_blocks()
        batch_predictions = [
            {"type": "ABSTRACT", "confidence": 0.9},
            {"type": "METHODOLOGY", "confidence": 0.85},
            {"type": "CONCLUSION", "confidence": 0.88},
        ]

        parser.model = object()
        parser.tokenizer = object()
        parser._load_model = MagicMock()

        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False),
            patch.object(parser, "_repair_fragmented_headings", return_value=blocks),
            patch.object(parser, "_predict_block_types_batch", return_value=batch_predictions) as batch_mock,
            patch.object(
                parser,
                "_predict_block_type",
                side_effect=AssertionError("single-block classification should not be called"),
            ) as single_mock,
        ):
            result = parser.analyze_blocks(blocks)

        assert len(result) == len(blocks)
        assert result[0]["predicted_section_type"] == "ABSTRACT"
        assert result[1]["predicted_section_type"] == "METHODOLOGY"
        assert result[2]["predicted_section_type"] == "CONCLUSION"
        batch_mock.assert_called_once_with([block.text for block in blocks])
        assert single_mock.call_count == 0

    @pytest.mark.unit
    def test_batch_prediction_falls_back_to_heuristics_on_inference_error(self):
        parser = SemanticParser()
        parser.model = object()
        parser.tokenizer = MagicMock(side_effect=RuntimeError("tokenizer boom"))
        parser.remote_base_urls = []
        parser._last_good_remote_url = None

        with patch("app.pipeline.intelligence.semantic_parser.torch", object()):
            predictions = parser._predict_block_types_batch(
                ["Abstract", "Results and discussion paragraph."],
            )

        assert len(predictions) == 2
        assert predictions[0]["type"] == "ABSTRACT"
        assert "type" in predictions[1]
        assert "confidence" in predictions[1]

    @pytest.mark.unit
    def test_predict_blocks_batch_routes_to_batch_predictor(self):
        parser = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", False),
            patch.object(
                parser,
                "_predict_block_types_batch",
                return_value=[{"type": "BODY", "confidence": 0.5}],
            ) as batch_mock,
        ):
            output = parser.predict_blocks_batch(["Sample block text"])

        batch_mock.assert_called_once_with(["Sample block text"])
        assert output[0]["type"] == "BODY"

    @pytest.mark.unit
    def test_predict_blocks_batch_prefers_remote_scibert_when_configured(self):
        parser = SemanticParser()
        parser.remote_base_urls = ["https://scibert-primary.example", "https://scibert-shadow.example"]
        parser.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            return SimpleNamespace(
                status_code=200,
                json=lambda: {
                    "predictions": [
                        {"type": "ABSTRACT", "confidence": 0.91},
                        {"type": "METHODOLOGY", "confidence": 0.88},
                    ]
                },
            )

        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=True),
            patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post),
        ):
            output = parser.predict_blocks_batch(["Abstract text", "Methods text"])

        assert output[0]["type"] == "ABSTRACT"
        assert output[1]["type"] == "METHODOLOGY"
