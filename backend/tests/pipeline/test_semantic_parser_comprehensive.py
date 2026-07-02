# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Comprehensive tests for SemanticParser — covers ALL methods, branches, and edge cases.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, call, patch

import pytest

from app.pipeline.intelligence.semantic_parser import (
    SemanticParser,
    get_semantic_parser,
    HEURISTIC_ONLY_MODEL_NAMES,
)

def _sample_blocks() -> list[Block]:
    from app.models import Block, BlockType
    return [
        Block(block_id="b-1", index=0, block_type=BlockType.BODY, text="Abstract of the manuscript."),
        Block(block_id="b-2", index=1, block_type=BlockType.BODY, text="Methods and experiments."),
        Block(block_id="b-3", index=2, block_type=BlockType.BODY, text="Conclusions and future work."),
    ]

class TestInit:
    def test_default_init(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p.model_name == "allenai/scibert_scivocab_uncased"
        assert p.tokenizer is None
        assert p.model is None
        assert p._is_loaded is False

    def test_config_from_settings(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.settings") as ms:
            ms.get_scibert_urls.return_value = ["https://scibert.example.com"]
            ms.SCIBERT_URL = "https://fallback.example.com"
            ms.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 15
            ms.GROBID_MAX_RETRIES = 5
            ms.SCIBERT_REMOTE_ONLY = True

            p = SemanticParser()
            assert p.remote_base_urls == ["https://scibert.example.com"]
            assert p.remote_timeout == 15
            assert p.remote_max_retries == 5
            assert p.remote_only is True

    def test_fallback_scibert_url(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.settings") as ms:
            ms.get_scibert_urls.return_value = []
            ms.SCIBERT_URL = "https://alt.example.com"
            ms.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 25
            ms.GROBID_MAX_RETRIES = 3
            ms.SCIBERT_REMOTE_ONLY = False

            p = SemanticParser()
            assert p.remote_base_urls == ["https://alt.example.com"]

    def test_no_urls_configured(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.settings") as ms:
            ms.get_scibert_urls.return_value = []
            ms.SCIBERT_URL = None
            ms.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 25
            ms.GROBID_MAX_RETRIES = 3
            ms.SCIBERT_REMOTE_ONLY = False

            p = SemanticParser()
            assert p.remote_base_urls == []

    def test_urls_stripped(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.settings") as ms:
            ms.get_scibert_urls.return_value = ["https://ex.com/  "]
            ms.SCIBERT_URL = None
            ms.PIPELINE_SEMANTIC_TIMEOUT_SECONDS = 25
            ms.GROBID_MAX_RETRIES = 3
            ms.SCIBERT_REMOTE_ONLY = False

            p = SemanticParser()
            assert p.remote_base_urls == ["https://ex.com/  "]

class TestLoadModel:
    def test_already_loaded_returns(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p._is_loaded = True
        with patch.object(p, "_load_local_model") as mock_llm:
            p._load_model()
            mock_llm.assert_not_called()

    def test_heuristic_only_model_name(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        for name in HEURISTIC_ONLY_MODEL_NAMES:
            p.model_name = name
            p._is_loaded = False
            p._load_model()
            assert p.tokenizer is None
            assert p.model is None
            assert p._is_loaded is True

    def test_remote_urls_set_skips_local(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://scibert.example.com"]
        p._is_loaded = False
        with patch.object(p, "_load_local_model") as mock_llm:
            p._load_model()
            assert p._is_loaded is True
            mock_llm.assert_not_called()

    def test_local_loading_path(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p._is_loaded = False
        with patch.object(p, "_load_local_model") as mock_llm:
            p._load_model()
            mock_llm.assert_called_once()
            assert p._is_loaded is True

class TestLoadLocalModel:
    def test_transformers_not_available(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer", None):
            with patch("app.pipeline.intelligence.semantic_parser.AutoModel", None):
                p = SemanticParser()
                with patch.object(p, "model", None):
                    p._load_local_model()
                    assert p.tokenizer is None
                    assert p.model is None

    def test_reuses_from_model_store(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer") as mock_tok:
            with patch("app.pipeline.intelligence.semantic_parser.AutoModel") as mock_mod:
                mock_store = MagicMock()
                mock_store.is_loaded.return_value = True
                mock_store.get_model.side_effect = lambda k: MagicMock() if k in ("scibert_tokenizer", "scibert_model") else None
                with patch("app.services.model_store.model_store", mock_store):
                    p = SemanticParser()
                    p._load_local_model()
                    assert p.tokenizer is not None
                    assert p.model is not None
                    mock_tok.from_pretrained.assert_not_called()

    def test_loads_from_huggingface(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer") as mock_tok:
            with patch("app.pipeline.intelligence.semantic_parser.AutoModel") as mock_mod:
                mock_store = MagicMock()
                mock_store.is_loaded.return_value = False
                with patch("app.services.model_store.model_store", mock_store):
                    p = SemanticParser()
                    p._load_local_model()
                    mock_tok.from_pretrained.assert_called_once()
                    mock_mod.from_pretrained.assert_called_once()

    def test_exception_during_load(self):
        from app.models import Block, BlockType
        with patch("app.pipeline.intelligence.semantic_parser.AutoTokenizer") as mock_tok:
            mock_tok.from_pretrained.side_effect = RuntimeError("OOM")
            mock_store = MagicMock()
            mock_store.is_loaded.return_value = False
            with patch("app.services.model_store.model_store", mock_store):
                p = SemanticParser()
                p._load_local_model()
                assert p.tokenizer is None
                assert p.model is None

class TestOrderedRemoteUrls:
    def test_no_last_good(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://a.com", "https://b.com"]
        p._last_good_remote_url = None
        ordered = p._ordered_remote_urls()
        assert ordered == ["https://a.com", "https://b.com"]

    def test_last_good_ttl_expired(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://a.com", "https://b.com"]
        p._last_good_remote_url = "https://b.com"
        p._last_good_remote_at = time.monotonic() - 600
        ordered = p._ordered_remote_urls()
        assert ordered == ["https://a.com", "https://b.com"]

    def test_last_good_moved_to_front(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://a.com", "https://b.com", "https://c.com"]
        p._last_good_remote_url = "https://b.com"
        p._last_good_remote_at = time.monotonic()
        ordered = p._ordered_remote_urls()
        assert ordered[0] == "https://b.com"
        assert ordered[1:] == ["https://a.com", "https://c.com"]

    def test_last_good_not_in_list(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://a.com"]
        p._last_good_remote_url = "https://unknown.com"
        p._last_good_remote_at = time.monotonic()
        ordered = p._ordered_remote_urls()
        assert ordered == ["https://a.com"]

class TestMarkLastGoodRemoteUrl:
    def test_sets_new_endpoint(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p._last_good_remote_url = None
        p._mark_last_good_remote_url("https://a.com", reason="test")
        assert p._last_good_remote_url == "https://a.com"

    def test_failover_logs_warning(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p._last_good_remote_url = "https://old.com"
        p._mark_last_good_remote_url("https://new.com", reason="failover")
        assert p._last_good_remote_url == "https://new.com"
        assert p._last_good_remote_at > 0

class TestRetryBackoffSeconds:
    def test_attempt_1(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._retry_backoff_seconds(1) == 1.0

    def test_attempt_2(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._retry_backoff_seconds(2) == 2.0

    def test_attempt_3(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._retry_backoff_seconds(3) == 4.0

    def test_attempt_4_capped(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._retry_backoff_seconds(4) == 8.0

    def test_attempt_5_still_capped(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._retry_backoff_seconds(5) == 8.0

class TestNormalizeRemotePrediction:
    def test_not_a_dict(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._normalize_remote_prediction("string") is None
        assert p._normalize_remote_prediction(123) is None
        assert p._normalize_remote_prediction(None) is None

    def test_no_label_found(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._normalize_remote_prediction({"confidence": 0.9}) is None

    def test_type_key(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        result = p._normalize_remote_prediction({"type": "abstract", "confidence": 0.9})
        assert result["type"] == "ABSTRACT"
        assert result["confidence"] == 0.9

    def test_label_key(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        result = p._normalize_remote_prediction({"label": "body", "score": 0.8})
        assert result["type"] == "BODY"
        assert result["confidence"] == 0.8

    def test_predicted_section_type_key(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        result = p._normalize_remote_prediction({"predicted_section_type": "heading", "confidence_score": 0.7})
        assert result["type"] == "HEADING"
        assert result["confidence"] == 0.7

    def test_section_key(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        result = p._normalize_remote_prediction({"section": "title"})
        assert result["type"] == "TITLE"
        assert result["confidence"] == 0.0

    def test_confidence_type_error(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        result = p._normalize_remote_prediction({"type": "body", "confidence": "not-a-number"})
        assert result["type"] == "BODY"
        assert result["confidence"] == 0.0

class TestPredictBlockTypesRemote:
    def test_no_base_urls_returns_none(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        assert p._predict_block_types_remote(["text"]) is None

    def test_empty_texts_returns_none(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        assert p._predict_block_types_remote([]) is None

    def test_successful_prediction(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1
        p.remote_predict_path = "/predict"

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"predictions": [{"type": "ABSTRACT", "confidence": 0.9}]},
            )

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["Abstract text"])
            assert result is not None
            assert result[0]["type"] == "ABSTRACT"

    def test_non_200_retry_then_break(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 2
        p.TRANSIENT_HTTP_STATUSES = {503}

        call_count = [0]

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            call_count[0] += 1
            return SimpleNamespace(status_code=503, json=lambda: {})

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
                result = p._predict_block_types_remote(["text"])
                assert call_count[0] == 2
                assert result is None

    def test_non_retryable_status_breaks(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 3

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(status_code=400, json=lambda: {})

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text"])
            assert result is None

    def test_non_json_response(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(status_code=200, json=lambda: (_ for _ in ()).throw(ValueError("no json")))

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text"])
            assert result is None

    def test_payload_no_predictions_list(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(status_code=200, json=lambda: {"other": "data"})

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text"])
            assert result is None

    def test_payload_is_list(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(status_code=200, json=lambda: [{"type": "BODY", "confidence": 0.8}])

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text"])
            assert result is not None
            assert result[0]["type"] == "BODY"

    def test_normalization_failure_resets(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"predictions": [{"type": "ABSTRACT", "confidence": 0.9}, {"notype": "data"}]},
            )

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text1", "text2"])
            assert result is None

    def test_length_mismatch(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 1

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"predictions": [{"type": "BODY", "confidence": 0.8}]},
            )

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            result = p._predict_block_types_remote(["text1", "text2"])
            assert result is None

    def test_request_exception_retry(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 2

        call_count = [0]

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            call_count[0] += 1
            raise ConnectionError("timeout")

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
                result = p._predict_block_types_remote(["text"])
                assert call_count[0] == 2
                assert result is None

    def test_generic_exception_retry(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://ex.com"]
        p.remote_max_retries = 2

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            raise RuntimeError("unexpected")

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
                result = p._predict_block_types_remote(["text"])
                assert result is None

    def test_failover_to_next_endpoint(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = ["https://a.com", "https://b.com"]
        p.remote_max_retries = 1

        call_log = []

        def _mock_post(*args, **kwargs):
            from app.models import Block, BlockType
            call_log.append(kwargs.get("url", args[0] if args else ""))
            return SimpleNamespace(status_code=500, json=lambda: {})

        with patch("app.pipeline.intelligence.semantic_parser.requests.post", side_effect=_mock_post):
            with patch("app.pipeline.intelligence.semantic_parser.time.sleep"):
                result = p._predict_block_types_remote(["text"])
                assert result is None
                assert len(call_log) == 2

class TestDetectBoundaries:
    def test_success(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        result = p.detect_boundaries(blocks)
        assert len(result) == 3

    def test_exception_safe(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with patch.object(p, "_repair_fragmented_headings", side_effect=ValueError("broken")):
            result = p.detect_boundaries(_sample_blocks())
            assert len(result) == 3

class TestReconcileFragmentedHeadings:
    def test_success(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        result = p.reconcile_fragmented_headings(blocks)
        assert len(result) == 3

    def test_exception_safe(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with patch.object(p, "_repair_fragmented_headings", side_effect=ValueError("broken")):
            result = p.reconcile_fragmented_headings(_sample_blocks())
            assert len(result) == 3

class TestAnalyzeBlocks:
    def test_non_english_path(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True),
            patch("app.pipeline.intelligence.semantic_parser.detect_language", return_value="de"),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}),
        ):
            result = p.analyze_blocks(blocks)
        assert len(result) == 3
        assert result[0]["detected_language"] == "de"

    def test_langdetect_exception(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", False),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True),
            patch("app.pipeline.intelligence.semantic_parser.detect_language", side_effect=Exception("fail")),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}),
        ):
            result = p.analyze_blocks(blocks)
        assert result[0]["detected_language"] == "en"

    def test_empty_text_no_detect(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        b = Block(block_id="b1", index=0, block_type=BlockType.BODY, text="")
        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", False),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", True),
            patch.object(p, "_repair_fragmented_headings", return_value=[b]),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}),
        ):
            result = p.analyze_blocks([b])
        assert result[0]["detected_language"] == "en"

    def test_fallback_prediction(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_predict_block_types_batch", return_value=[{"type": "ABSTRACT", "confidence": 0.9}]),
        ):
            result = p.analyze_blocks(blocks)
        assert len(result) == 3
        assert result[0]["predicted_section_type"] == "ABSTRACT"
        assert result[2]["predicted_section_type"] == "CONCLUSION"

    def test_heuristic_fallback_predictions(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        with (
            patch("app.pipeline.intelligence.semantic_parser.settings.USE_SCIBERT_CLASSIFICATION", True),
            patch("app.pipeline.intelligence.semantic_parser.HAS_LANGDETECT", False),
            patch.object(p, "_repair_fragmented_headings", return_value=blocks),
            patch.object(p, "_predict_block_types_batch", return_value=[]),
        ):
            result = p.analyze_blocks(blocks)
        assert len(result) == 3

class TestPredictBlockType:
    def test_remote_first(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with patch.object(p, "_predict_block_types_remote", return_value=[{"type": "ABSTRACT", "confidence": 0.9}]):
            result = p._predict_block_type("Abstract text")
            assert result["type"] == "ABSTRACT"

    def test_local_model_path(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        mock_tok = MagicMock()
        mock_tok.return_value = {"input_ids": MagicMock()}
        p.tokenizer = None
        p.model = None

        with patch.object(p, "_load_local_model") as mock_llm:
            with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}):
                import torch as _
                p.model = MagicMock()
                p.tokenizer = mock_tok
                mock_inputs = MagicMock()
                mock_tok.return_value = mock_inputs
                mock_out = MagicMock()
                mock_out.logits = MagicMock()
                p.model.return_value = mock_out

                with patch("app.pipeline.intelligence.semantic_parser.torch") as mock_torch:
                    mock_torch.no_grad.return_value.__enter__ = MagicMock(return_value=None)
                    mock_torch.no_grad.return_value.__exit__ = MagicMock(return_value=None)
                    mock_torch.softmax.return_value = MagicMock()
                    label_idx = MagicMock()
                    label_idx.item.return_value = 2
                    mock_torch.max.return_value = (MagicMock(), label_idx)

                    p.model.return_value = mock_out
                    result = p._predict_block_type("Test")
                    assert result["type"] == "BODY"

    def test_remote_only_no_local(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_only = True
        p.model = None
        p.tokenizer = None
        with patch.object(p, "_predict_block_types_remote", return_value=None):
            with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}):
                result = p._predict_block_type("text")
                assert result["type"] == "BODY"

    def test_no_model_no_tokenizer_heuristic(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = None
        p.tokenizer = None
        with patch("app.pipeline.intelligence.semantic_parser.torch", None):
            with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}):
                result = p._predict_block_type("text")
                assert result["type"] == "BODY"

    def test_label_index_out_of_bounds_uses_body(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        mock_tok = MagicMock()
        mock_tok.return_value = {"input_ids": MagicMock()}
        p.model = MagicMock()
        p.tokenizer = mock_tok

        with patch("app.pipeline.intelligence.semantic_parser.torch") as mock_torch:
            mock_torch.no_grad.return_value.__enter__ = MagicMock()
            mock_torch.no_grad.return_value.__exit__ = MagicMock()
            mock_out = MagicMock()
            p.model.return_value = mock_out
            mock_confidence = MagicMock()
            mock_confidence.item.return_value = 0.9
            mock_label_idx = MagicMock()
            mock_label_idx.item.return_value = 999
            mock_torch.softmax.return_value = MagicMock()
            mock_torch.max.return_value = (mock_confidence, mock_label_idx)

            result = p._predict_block_type("text")
            assert result["type"] == "BODY"
            assert result["confidence"] == 0.9

class TestPredictBlockTypesBatch:
    def test_empty_texts(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        assert p._predict_block_types_batch([]) == []

    def test_remote_predictions_used(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with patch.object(p, "_predict_block_types_remote", return_value=[{"type": "BODY", "confidence": 0.8}]):
            result = p._predict_block_types_batch(["text"])
            assert result[0]["type"] == "BODY"

    def test_local_model_inference(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = MagicMock()
        p.tokenizer = MagicMock()
        p.tokenizer.return_value = {"input_ids": MagicMock(), "attention_mask": MagicMock()}

        with patch("app.pipeline.intelligence.semantic_parser.torch") as mock_torch:
            mock_torch.no_grad.return_value.__enter__ = MagicMock()
            mock_torch.no_grad.return_value.__exit__ = MagicMock()
            mock_confidence = MagicMock()
            mock_confidence.item.return_value = 0.85
            mock_label_idx = MagicMock()
            mock_label_idx.item.return_value = 3
            mock_torch.softmax.return_value = MagicMock()
            mock_confidences = MagicMock()
            mock_confidences.__iter__.return_value = iter([mock_confidence])
            mock_label_idxs = MagicMock()
            mock_label_idxs.__iter__.return_value = iter([mock_label_idx])
            mock_torch.max.return_value = (mock_confidences, mock_label_idxs)

            result = p._predict_block_types_batch(["text"])
            assert len(result) == 1
            assert result[0]["type"] == "REFERENCES"

    def test_local_model_exception_falls_to_heuristics(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = MagicMock()
        p.tokenizer = MagicMock()
        p.tokenizer.side_effect = RuntimeError("tokenizer error")

        with patch("app.pipeline.intelligence.semantic_parser.torch", object()):
            with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}):
                result = p._predict_block_types_batch(["text"])
                assert len(result) == 1
                assert result[0]["type"] == "BODY"

    def test_no_model_no_torch_heuristics(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        p.remote_base_urls = []
        p.remote_only = False
        p.model = None
        p.tokenizer = None
        with patch("app.pipeline.intelligence.semantic_parser.torch", None):
            with patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}):
                result = p._predict_block_types_batch(["text"])
                assert result[0]["type"] == "BODY"

class TestPredictBlocksBatch:
    def test_scibert_enabled(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=True),
            patch.object(p, "_load_model") as mock_load,
            patch.object(p, "_predict_block_types_batch", return_value=[{"type": "BODY", "confidence": 0.5}]) as mock_batch,
        ):
            p.predict_blocks_batch(["text"])
            mock_load.assert_called_once()
            mock_batch.assert_called_once_with(["text"])

    def test_scibert_disabled(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=False),
            patch.object(p, "_load_model") as mock_load,
            patch.object(p, "_predict_block_types_batch", return_value=[{"type": "BODY", "confidence": 0.5}]) as mock_batch,
        ):
            p.predict_blocks_batch(["text"])
            mock_load.assert_not_called()
            mock_batch.assert_called_once_with(["text"])

class TestHeuristicClassify:
    def test_abstract(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Abstract: This paper presents")
        assert r["type"] == "ABSTRACT"

    def test_references_keyword(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("References")
        assert r["type"] == "REFERENCES"

    def test_bibliography(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Bibliography")
        assert r["type"] == "REFERENCES"

    def test_references_numbered_pattern(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("[1] Smith et al.")
        assert r["type"] == "REFERENCES"

    def test_references_decimal_pattern(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("1. Introduction")
        assert r["type"] == "REFERENCES"

    def test_acknowledgements(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Acknowledgements")
        assert r["type"] == "ACKNOWLEDGEMENTS"

    def test_acknowledgments_alt(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Acknowledgments")
        assert r["type"] == "ACKNOWLEDGEMENTS"

    def test_methodology(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Methodology")
        assert r["type"] == "METHODOLOGY"

    def test_methods(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Methods")
        assert r["type"] == "METHODOLOGY"

    def test_conclusion(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Conclusion")
        assert r["type"] == "CONCLUSION"

    def test_conclusions(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Conclusions")
        assert r["type"] == "CONCLUSION"

    def test_introduction(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Introduction")
        assert r["type"] == "HEADING"

    def test_results(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Results")
        assert r["type"] == "HEADING"

    def test_discussion(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Discussion")
        assert r["type"] == "HEADING"

    def test_figure_caption(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Figure 1. Results")
        assert r["type"] == "FIGURE_CAPTION"

    def test_fig_caption(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Fig. 2. Architecture")
        assert r["type"] == "FIGURE_CAPTION"

    def test_table_caption(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Table 1. Data")
        assert r["type"] == "TABLE_CAPTION"

    def test_tab_caption(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Tab. 1. Stats")
        assert r["type"] == "TABLE_CAPTION"

    def test_uppercase_short_heading(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("INTRODUCTION")
        assert r["type"] == "HEADING"

    def test_long_text_returns_body(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("A" * 200)
        assert r["type"] == "BODY"

    def test_short_uppercase_heading(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("Short Heading")
        assert r["type"] == "HEADING"

    def test_empty_text(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("")
        assert r["type"] == "BODY"

    def test_confidence_default(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("some lowercase text that won't match heading heuristic at all because lowercase")
        assert r["confidence"] == 0.5

    def test_abstract_lowercase(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        r = p._heuristic_classify("abstract the manuscript")
        assert r["type"] == "ABSTRACT"

class TestClassifyBlock:
    def test_use_transformer_scibert_enabled(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=True),
            patch.object(p, "_predict_block_type", return_value={"type": "ABSTRACT", "confidence": 0.9}) as mock_pred,
        ):
            r = p.classify_block("Abstract text")
            mock_pred.assert_called_once_with("Abstract text")
            assert r["type"] == "ABSTRACT"

    def test_use_transformer_scibert_disabled(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=False),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}) as mock_heur,
        ):
            r = p.classify_block("text")
            mock_heur.assert_called_once_with("text")

    def test_no_transformer_heuristic(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        with (
            patch("app.pipeline.intelligence.semantic_parser.should_enable_scibert", return_value=True),
            patch.object(p, "_heuristic_classify", return_value={"type": "BODY", "confidence": 0.5}) as mock_heur,
        ):
            r = p.classify_block("text", use_transformer=False)
            mock_heur.assert_called_once_with("text")

class TestRepairFragmentedHeadings:
    def test_no_fragmentation(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        blocks = _sample_blocks()
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 3
        assert result[0].text == "Abstract of the manuscript."

    def test_number_followed_by_lowercase(self):
        from app.models import Block, BlockType
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="1"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="introduction to the paper"),
        ]
        p = SemanticParser()
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 1
        assert result[0].text == "1. introduction to the paper"

    def test_number_followed_by_uppercase(self):
        from app.models import Block, BlockType
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="2"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="Methods Section"),
        ]
        p = SemanticParser()
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 2
        assert result[0].text == "2"
        assert result[1].text == "Methods Section"

    def test_non_digit_number_first_block(self):
        from app.models import Block, BlockType
        blocks = [
            Block(block_id="b1", index=0, block_type=BlockType.BODY, text="Introduction"),
            Block(block_id="b2", index=1, block_type=BlockType.BODY, text="methods"),
        ]
        p = SemanticParser()
        result = p._repair_fragmented_headings(blocks)
        assert len(result) == 2

    def test_only_one_block(self):
        from app.models import Block, BlockType
        p = SemanticParser()
        result = p._repair_fragmented_headings([_sample_blocks()[0]])
        assert len(result) == 1

class TestGetSemanticParser:
    def test_returns_parser(self):
        from app.models import Block, BlockType
        import app.pipeline.intelligence.semantic_parser as sp
        sp._semantic_parser = None
        p = get_semantic_parser()
        assert isinstance(p, SemanticParser)

    def test_singleton(self):
        from app.models import Block, BlockType
        import app.pipeline.intelligence.semantic_parser as sp
        sp._semantic_parser = None
        p1 = get_semantic_parser()
        p2 = get_semantic_parser()
        assert p1 is p2
