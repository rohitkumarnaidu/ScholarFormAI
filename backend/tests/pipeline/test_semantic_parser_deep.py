# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Deep coverage tests for SemanticParser — targets remaining uncovered lines/branches.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.pipeline]


class TestRemoteRequestException:
    """Cover lines 269-279: `except RequestException` handler body with retry."""

    def test_request_exception_retries_and_continues(self):
        from requests.exceptions import RequestException

        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 2

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=RequestException("conn reset")):
            with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
                result = p._predict_block_types_remote(["text"])
                assert result is None

    def test_request_exception_last_attempt_breaks(self):
        from requests.exceptions import RequestException

        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=RequestException("timeout")):
            with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
                result = p._predict_block_types_remote(["text"])
                assert result is None


class TestRemoteForLoopSkip:
    """Cover branch 208->293: for-loop body skipped when max_retries=0."""

    def test_max_retries_zero_skips_inner_loop(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 0

        with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
            result = p._predict_block_types_remote(["text"])
            assert result is None


class TestRemotePayloadNotDictOrList:
    """Cover branch 242->245: payload is neither dict nor list."""

    def test_payload_is_string(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            return SimpleNamespace(status_code=200, json=lambda: "error")

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text"])
            assert result is None


class TestPredictBlockTypeEdgeCases:
    """Additional edge-case coverage for _predict_block_type."""

    def test_local_model_already_loaded_skips_reload(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = MagicMock()
        p.tokenizer = MagicMock()

        with patch.object(p, "_load_local_model") as mock_llm:
            with patch("app.pipeline.intelligence.semantic_parser.torch", None):
                result = p._predict_block_type("text")
                assert result["type"] == "BODY"
                mock_llm.assert_not_called()

    def test_remote_prediction_returns_none_loads_local_then_heuristic(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = None
        p.tokenizer = None

        with patch.object(p, "_predict_block_types_remote", return_value=None):
            with patch.object(p, "_load_local_model"):
                with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}) as mock_heur:
                    result = p._predict_block_type("text")
                    assert result["type"] == "BODY"
                    mock_heur.assert_called_once()


class TestPredictBlocksBatchEdgeCases:
    """Additional edge-case coverage for predict_blocks_batch."""

    def test_batch_local_model_already_loaded(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = MagicMock()
        p.tokenizer = MagicMock()

        with patch("app.pipeline.intelligence.semantic_parser.torch", None):
            result = p._predict_block_types_batch(["text"])
            assert len(result) == 1
            assert result[0]["type"] == "BODY"

    def test_batch_remote_returns_none_loads_local_then_heuristic(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = None
        p.tokenizer = None

        with patch.object(p, "_predict_block_types_remote", return_value=None):
            with patch.object(p, "_load_local_model"):
                with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}):
                    result = p._predict_block_types_batch(["text"])
                    assert len(result) == 1


class TestHeuristicClassifyEdgeCases:
    """Additional edge-case coverage for _heuristic_classify."""

    def test_none_text(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        r = p._heuristic_classify(None)
        assert r["type"] == "BODY"

    def test_short_lowercase_heading_candidate(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        r = p._heuristic_classify("Related Work")
        assert r["type"] == "HEADING"
        assert r["confidence"] == 0.6


class TestAnalyzeBlocksEdgeCases:
    """Additional edge-case coverage for analyze_blocks."""

    def test_non_english_uses_heuristic(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="Abstract."),
        ]

        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True),
            patch("app.pipeline.intelligence.semantic_parser.detect_language", return_value="fr"),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}),
            patch.object(p, "_predict_block_types_batch") as mock_batch,
        ):
            result = p.analyze_blocks(blocks)

        assert len(result) == 1
        assert result[0]["detected_language"] == "fr"
        mock_batch.assert_not_called()

    def test_scibert_enabled_uses_batch(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="Abstract."),
        ]

        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True),
            patch("app.pipeline.intelligence.semantic_parser.detect_language", return_value="en"),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_predict_block_types_batch", return_value=[{"type": "ABSTRACT", "confidence": 0.9}]) as mock_batch,
        ):
            result = p.analyze_blocks(blocks)

        assert result[0]["predicted_section_type"] == "ABSTRACT"
        mock_batch.assert_called_once()

    def test_combined_text_empty_skips_detect(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="   "),
        ]

        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", False),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True),
            patch("app.pipeline.intelligence.semantic_parser.detect_language") as mock_detect,
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}),
        ):
            result = p.analyze_blocks(blocks)

        assert result[0]["detected_language"] == "en"
        mock_detect.assert_not_called()

    def test_predictions_shorter_than_blocks_falls_back(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="One."),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="Two."),
        ]

        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_predict_block_types_batch", return_value=[{"type": "ABSTRACT", "confidence": 0.9}]),
        ):
            result = p.analyze_blocks(blocks)

        assert len(result) == 2
        assert result[0]["predicted_section_type"] == "ABSTRACT"
        assert result[1]["predicted_section_type"] == "HEADING"


class TestClassifyBlockEdgeCases:
    """Additional edge-case coverage for classify_block."""

    def test_use_transformer_true_scibert_disabled(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=False),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}) as mock_heur,
        ):
            r = p.classify_block("text", use_transformer=True)
            mock_heur.assert_called_once_with("text")
            assert r["type"] == "BODY"


class TestRepairFragmentedHeadingsEdgeCases:
    """Additional edge-case coverage for _repair_fragmented_headings."""

    def test_number_with_space_before_lowercase(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="42"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="is the answer"),
        ]
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 1
        assert result[0].text == "42. is the answer"

    def test_consecutive_numbers_merged(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="1"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="introduction"),
            Block(block_id="b3", index=2, block_type=BlockType.BODY, text="2"),
            Block(block_id="b4", index=3, block_type=BlockType.BODY, text="methods"),
        ]
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 2
        assert result[0].text == "1. introduction"
        assert result[1].text == "2. methods"

    def test_number_at_end(self):
        from app.models import Block, BlockType
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="Some text"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="5"),
        ]
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 2


class TestEndpointSuffixEdgeCases:
    """Cover line 205: endpoint suffix construction when not starting with /."""

    def test_remote_predict_path_without_leading_slash(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1
        p.remote_predict_path = "predict"

        def _mock_post(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            assert url == "https://ex.com/predict"
            return SimpleNamespace(status_code=200, json=lambda: {"predictions": [{"type": "BODY", "confidence": 0.9}]})

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text"])
            assert result is not None
            assert result[0]["type"] == "BODY"


class TestLoadModelEdgeCases:
    """Additional edge-case coverage for _load_model and _load_local_model."""

    def test_load_local_model_store_returns_false_loads_from_huggingface(self):
        from app.pipeline.intelligence.semantic_parser import SemanticParser

        mock_store = MagicMock()
        mock_store.is_loaded.return_value = False

        with patch("app.services.model_store.model_store", mock_store):
            with patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer") as mock_tok:
                with patch("app.pipeline.intelligence.semantic_parser.AutoModel") as mock_mod:
                    p = SemanticParser()
                    p.remote_base_urls = []
                    p._is_loaded = False
                    p._load_model()
                    assert p._is_loaded is True
                    mock_tok.from_pretrained.assert_called_once()
                    mock_mod.from_pretrained.assert_called_once()
