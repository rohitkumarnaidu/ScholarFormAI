# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging
import re
import time
from typing import Any, Dict, List, Optional

import requests
from requests import RequestException

try:
    import torch
except ImportError:  # pragma: no cover - dependency specific
    torch = None

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, logging as transformers_logging
except ImportError:  # pragma: no cover - dependency specific
    AutoTokenizer = None
    AutoModelForSequenceClassification = None

    class _TransformersLoggingNoop:
        @staticmethod
        def set_verbosity_error() -> None:
            return

    transformers_logging = _TransformersLoggingNoop()

from app.config.settings import settings
from app.models import Block, BlockType, PipelineDocument as Document
from app.pipeline.safety import safe_function
from app.services.scibert_gate import should_enable_scibert
from app.utils.singleton import get_or_create

# Backward-compat alias for tests and legacy patches.
AutoModel = AutoModelForSequenceClassification

try:
    from langdetect import detect as detect_language

    HAS_LANGDETECT = True
except ImportError:  # pragma: no cover - dependency specific
    HAS_LANGDETECT = False
    detect_language = None

logger = logging.getLogger(__name__)

HEURISTIC_ONLY_MODEL_NAMES = {
    "__heuristic_fallback__",
    "__local_benchmark_fallback__",
}

transformers_logging.set_verbosity_error()


class SemanticParser:
    """
    NLP semantic layer for manuscript block classification.

    Execution order:
    1) Remote SciBERT endpoint(s) when SCIBERT_URL/SCIBERT_URLS are configured
    2) Local SciBERT model (optional fallback)
    3) Deterministic heuristics
    """

    TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504, 520, 522, 524}
    LAST_GOOD_ENDPOINT_TTL_SECONDS = 300.0

    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._is_loaded = False

        configured_urls = list(getattr(settings, "get_scibert_urls", lambda: [])())
        if not configured_urls:
            fallback_url = getattr(settings, "SCIBERT_URL", None)
            if fallback_url:
                configured_urls = [str(fallback_url).rstrip("/")]

        self.remote_base_urls = [url.rstrip("/") for url in configured_urls if str(url).strip()]
        self.remote_predict_path = "/predict"
        self.remote_timeout = max(5, int(getattr(settings, "PIPELINE_SEMANTIC_TIMEOUT_SECONDS", 25)))
        self.remote_max_retries = max(1, int(getattr(settings, "GROBID_MAX_RETRIES", 3)))
        self.remote_only = bool(getattr(settings, "SCIBERT_REMOTE_ONLY", False))
        self._last_good_remote_url = self.remote_base_urls[0] if self.remote_base_urls else None
        self._last_good_remote_at = time.monotonic()

    def _load_model(self) -> None:
        """Lazily initialize semantic inference strategy."""
        if self._is_loaded:
            return

        if self.model_name in HEURISTIC_ONLY_MODEL_NAMES:
            logger.info(
                "SemanticParser: using heuristic-only profile for %s.",
                self.model_name,
            )
            self.tokenizer = None
            self.model = None
            self._is_loaded = True
            return

        if self.remote_base_urls:
            logger.info(
                "SemanticParser: remote SciBERT endpoints configured; using remote-first inference."
            )
            self._is_loaded = True
            return

        self._load_local_model()
        self._is_loaded = True

    def _load_local_model(self) -> None:
        """Load local SciBERT model when remote inference is unavailable or disabled."""
        if AutoTokenizer is None or AutoModel is None:
            logger.warning(
                "SemanticParser: transformers not available; using heuristic-only mode."
            )
            self.tokenizer = None
            self.model = None
            return

        from app.services.model_store import model_store

        if model_store.is_loaded("scibert_tokenizer") and model_store.is_loaded("scibert_model"):
            self.tokenizer = model_store.get_model("scibert_tokenizer")
            self.model = model_store.get_model("scibert_model")
            logger.info("SemanticParser: reusing global SciBERT from ModelStore.")
            return

        logger.info("SemanticParser: loading local SciBERT model (%s)...", self.model_name)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)  # nosec
            logger.warning(
                "Initializing SciBERT classification head from base weights. "
                "Predictions improve with fine-tuned checkpoints."
            )
            self.model = AutoModel.from_pretrained(
                self.model_name,  # nosec
                ignore_mismatched_sizes=True,
            )
            logger.info("SemanticParser: local SciBERT loaded.")
        except Exception as exc:
            logger.warning("SemanticParser: local model load failed (%s).", exc)
            self.tokenizer = None
            self.model = None

    def _ordered_remote_urls(self) -> List[str]:
        ordered = list(self.remote_base_urls)
        if (
            self._last_good_remote_url
            and self._last_good_remote_url in ordered
            and (time.monotonic() - self._last_good_remote_at) <= self.LAST_GOOD_ENDPOINT_TTL_SECONDS
        ):
            ordered.remove(self._last_good_remote_url)
            ordered.insert(0, self._last_good_remote_url)
        return ordered

    def _mark_last_good_remote_url(self, base_url: str, *, reason: str) -> None:
        previous = self._last_good_remote_url
        self._last_good_remote_url = base_url
        self._last_good_remote_at = time.monotonic()
        if previous and previous != base_url:
            logger.warning(
                "SciBERT failover switch: %s -> %s (reason=%s)",
                previous,
                base_url,
                reason,
            )

    def _retry_backoff_seconds(self, attempt: int) -> float:
        return min(float(2 ** max(0, attempt - 1)), 8.0)

    def _normalize_remote_prediction(self, item: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        label = (
            item.get("type")
            or item.get("label")
            or item.get("predicted_section_type")
            or item.get("section")
        )
        if not label:
            return None

        try:
            confidence = float(
                item.get("confidence")
                or item.get("score")
                or item.get("confidence_score")
                or 0.0
            )
        except (TypeError, ValueError):
            confidence = 0.0

        return {"type": str(label).strip().upper(), "confidence": confidence}

    def _predict_block_types_remote(self, texts: List[str]) -> Optional[List[Dict[str, Any]]]:
        if not self.remote_base_urls or not texts:
            return None

        endpoint_suffix = self.remote_predict_path if self.remote_predict_path.startswith("/") else f"/{self.remote_predict_path}"
        for endpoint_index, base_url in enumerate(self._ordered_remote_urls(), start=1):
            endpoint = f"{base_url.rstrip('/')}{endpoint_suffix}"
            for attempt in range(1, self.remote_max_retries + 1):
                try:
                    response = requests.post(
                        endpoint,
                        json={"texts": texts},
                        timeout=(3.0, float(self.remote_timeout)),
                    )

                    if response.status_code != 200:
                        logger.warning(
                            "SciBERT remote call failed: endpoint=%s status=%s attempt=%s/%s",
                            endpoint,
                            response.status_code,
                            attempt,
                            self.remote_max_retries,
                        )
                        if (
                            response.status_code in self.TRANSIENT_HTTP_STATUSES
                            and attempt < self.remote_max_retries
                        ):
                            time.sleep(self._retry_backoff_seconds(attempt))
                            continue
                        break

                    payload: Any
                    try:
                        payload = response.json()
                    except ValueError:
                        logger.warning("SciBERT remote returned non-JSON payload from %s.", endpoint)
                        break

                    raw_predictions: Any = None
                    if isinstance(payload, dict):
                        raw_predictions = payload.get("predictions") or payload.get("results")
                    elif isinstance(payload, list):
                        raw_predictions = payload

                    if not isinstance(raw_predictions, list):
                        logger.warning("SciBERT remote payload missing prediction list: endpoint=%s", endpoint)
                        break

                    normalized: List[Dict[str, Any]] = []
                    for item in raw_predictions:
                        norm = self._normalize_remote_prediction(item)
                        if norm is None:
                            normalized = []
                            break
                        normalized.append(norm)

                    if len(normalized) != len(texts):
                        logger.warning(
                            "SciBERT remote prediction length mismatch: expected=%s got=%s endpoint=%s",
                            len(texts),
                            len(normalized),
                            endpoint,
                        )
                        break

                    self._mark_last_good_remote_url(base_url, reason="predict_batch")
                    return normalized
                except RequestException as exc:
                    logger.warning(
                        "SciBERT remote request error: endpoint=%s attempt=%s/%s error=%s",
                        endpoint,
                        attempt,
                        self.remote_max_retries,
                        exc,
                    )
                    if attempt < self.remote_max_retries:
                        time.sleep(self._retry_backoff_seconds(attempt))
                        continue
                    break
                except Exception as exc:
                    logger.warning(
                        "SciBERT remote inference exception: endpoint=%s attempt=%s/%s error=%s",
                        endpoint,
                        attempt,
                        self.remote_max_retries,
                        exc,
                    )
                    if attempt < self.remote_max_retries:
                        time.sleep(min(float(attempt), 2.0))
                        continue
                    break

            if endpoint_index < len(self.remote_base_urls):
                next_endpoint = self._ordered_remote_urls()[endpoint_index]
                logger.warning(
                    "SciBERT failover: moving to next endpoint (from=%s to=%s)",
                    base_url,
                    next_endpoint,
                )

        return None

    def detect_boundaries(self, blocks: List[Block]) -> List[Block]:
        try:
            return self._repair_fragmented_headings(blocks)
        except Exception as exc:
            logger.warning(
                "SemanticParser Guard: detect_boundaries failed: %s. Returning original blocks.",
                exc,
            )
            return blocks

    def reconcile_fragmented_headings(self, blocks: List[Block]) -> List[Block]:
        try:
            return self._repair_fragmented_headings(blocks)
        except Exception as exc:
            logger.warning(
                "SemanticParser Guard: reconcile_fragmented_headings failed: %s. Returning original blocks.",
                exc,
            )
            return blocks

    @safe_function(fallback_value=[], error_message="SemanticParser.analyze_blocks failed")
    def analyze_blocks(self, blocks: List[Block]) -> List[Dict[str, Any]]:
        scibert_enabled = should_enable_scibert()
        if scibert_enabled:
            self._load_model()

        semantic_blocks: List[Dict[str, Any]] = []
        combined_text = " ".join(b.text for b in blocks[:10] if b.text)[:500]
        detected_lang = "en"
        if HAS_LANGDETECT and combined_text.strip():
            try:
                detected_lang = detect_language(combined_text)
            except Exception:
                detected_lang = "en"

        use_semantic_model = scibert_enabled and detected_lang == "en"
        if not use_semantic_model and detected_lang != "en":
            logger.warning(
                "Non-English document detected (%s). Using heuristic-only mode.",
                detected_lang,
            )

        repaired_blocks = self._repair_fragmented_headings(blocks)
        texts = [block.text or "" for block in repaired_blocks]
        if use_semantic_model:
            predictions = self._predict_block_types_batch(texts)
        else:
            predictions = [self._heuristic_classify(text) for text in texts]

        for i, block in enumerate(repaired_blocks):
            prediction = predictions[i] if i < len(predictions) else self._heuristic_classify(block.text)
            semantic_block = {
                "block_id": i,
                "raw_text": block.text,
                "predicted_section_type": prediction["type"],
                "confidence_score": prediction["confidence"],
                "detected_language": detected_lang,
            }
            semantic_blocks.append(semantic_block)

        return semantic_blocks

    def _predict_block_type(self, text: str) -> Dict[str, Any]:
        remote_predictions = self._predict_block_types_remote([text])
        if remote_predictions:
            return remote_predictions[0]

        if (self.model is None or self.tokenizer is None) and not self.remote_only:
            self._load_local_model()

        if not self.model or not self.tokenizer or torch is None:
            return self._heuristic_classify(text)

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            confidence, label_idx = torch.max(probs, dim=1)

        labels = [
            "HEADING",
            "ABSTRACT",
            "BODY",
            "REFERENCES",
            "FIGURE_CAPTION",
            "TABLE_CAPTION",
            "ACKNOWLEDGEMENTS",
            "EQUATION",
            "METHODOLOGY",
            "CONCLUSION",
            "AUTHOR_INFO",
            "TITLE",
        ]
        predicted_label = labels[label_idx.item()] if label_idx.item() < len(labels) else "BODY"
        return {"type": predicted_label, "confidence": float(confidence.item())}

    def _predict_block_types_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        if not texts:
            return []

        remote_predictions = self._predict_block_types_remote(texts)
        if remote_predictions is not None:
            return remote_predictions

        if (self.model is None or self.tokenizer is None) and not self.remote_only:
            self._load_local_model()

        if not self.model or not self.tokenizer or torch is None:
            return [self._heuristic_classify(text) for text in texts]

        try:
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            )
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=1)
                confidences, label_idxs = torch.max(probs, dim=1)

            labels = [
                "HEADING",
                "ABSTRACT",
                "BODY",
                "REFERENCES",
                "FIGURE_CAPTION",
                "TABLE_CAPTION",
                "ACKNOWLEDGEMENTS",
                "EQUATION",
                "METHODOLOGY",
                "CONCLUSION",
                "AUTHOR_INFO",
                "TITLE",
            ]

            results: List[Dict[str, Any]] = []
            for conf, idx in zip(confidences, label_idxs):
                label_index = idx.item()
                predicted_label = labels[label_index] if label_index < len(labels) else "BODY"
                results.append({"type": predicted_label, "confidence": float(conf.item())})
            return results
        except Exception as exc:
            logger.warning(
                "SemanticParser: local batch inference failed (%s). Falling back to heuristics.",
                exc,
            )
            return [self._heuristic_classify(text) for text in texts]

    def predict_blocks_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        if should_enable_scibert():
            self._load_model()
        return self._predict_block_types_batch(texts)

    def _heuristic_classify(self, text: str) -> Dict[str, Any]:
        prediction = {"type": "BODY", "confidence": 0.5}
        text = (text or "").strip()
        upper_text = text.upper()

        if len(text) < 150:
            if upper_text.startswith("ABSTRACT"):
                prediction = {"type": "ABSTRACT", "confidence": 0.8}
            elif upper_text.startswith("REFERENCES") or upper_text.startswith("BIBLIOGRAPHY"):
                prediction = {"type": "REFERENCES", "confidence": 0.8}
            elif re.match(r"^\[\d+\]", text) or re.match(r"^\d+\.\s+[A-Z]", text):
                prediction = {"type": "REFERENCES", "confidence": 0.75}
            elif upper_text.startswith("ACKNOWLEDGEMENTS") or upper_text.startswith("ACKNOWLEDGMENTS"):
                prediction = {"type": "ACKNOWLEDGEMENTS", "confidence": 0.8}
            elif upper_text.startswith("METHODOLOGY") or upper_text.startswith("METHODS"):
                prediction = {"type": "METHODOLOGY", "confidence": 0.8}
            elif upper_text.startswith("CONCLUSION") or upper_text.startswith("CONCLUSIONS"):
                prediction = {"type": "CONCLUSION", "confidence": 0.8}
            elif upper_text.startswith("INTRODUCTION"):
                prediction = {"type": "HEADING", "confidence": 0.8}
            elif upper_text.startswith("RESULTS") or upper_text.startswith("DISCUSSION"):
                prediction = {"type": "HEADING", "confidence": 0.8}
            elif text.startswith("Figure") or text.startswith("Fig."):
                prediction = {"type": "FIGURE_CAPTION", "confidence": 0.7}
            elif text.startswith("Table") or text.startswith("Tab."):
                prediction = {"type": "TABLE_CAPTION", "confidence": 0.7}
            elif text and text[0].isupper() and len(text) < 80:
                prediction = {"type": "HEADING", "confidence": 0.6}
        return prediction

    def classify_block(self, text: str, use_transformer: bool = True) -> Dict[str, Any]:
        if should_enable_scibert() and use_transformer:
            return self._predict_block_type(text)
        return self._heuristic_classify(text)

    def _repair_fragmented_headings(self, blocks: List[Block]) -> List[Block]:
        repaired = []
        i = 0
        while i < len(blocks):
            current = blocks[i]
            if i + 1 < len(blocks):
                next_block = blocks[i + 1]
                if current.text.isdigit() and next_block.text and next_block.text[0].islower():
                    current.text = f"{current.text}. {next_block.text}"
                    repaired.append(current)
                    i += 2
                    continue
            repaired.append(current)
            i += 1
        return repaired


_semantic_parser = None


def get_semantic_parser() -> SemanticParser:
    global _semantic_parser
    _semantic_parser = get_or_create(_semantic_parser, SemanticParser)
    return _semantic_parser

