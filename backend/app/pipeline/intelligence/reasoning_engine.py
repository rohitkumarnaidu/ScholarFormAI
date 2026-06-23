# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import json
import os
import re
import sys
import time
import logging
from typing import List, Dict, Any, Optional
import requests
from app.pipeline.safety.retry_guard import retry_guard
from app.pipeline.safety.circuit_breaker import circuit_breaker
from app.pipeline.safety.llm_validator import guard_llm_output
from pydantic import BaseModel, Field
from app.config.settings import settings
from app.utils.singleton import get_or_create

logger = logging.getLogger(__name__)
MAX_BLOCKS_PER_CALL = 30

class SemanticBlockSchema(BaseModel):
    block_id: str
    semantic_type: str
    confidence: float

class InstructionSetSchema(BaseModel):
    blocks: List[SemanticBlockSchema]
    fallback: bool = Field(default=False)
    model: Optional[str] = None
    latency: Optional[float] = None


def _instruction_set_circuit_fallback(
    engine: "ReasoningEngine",
    semantic_blocks: List[Dict[str, Any]],
    rules: str,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Circuit-breaker fallback for generate_instruction_set.
    Uses deterministic rule-based classification so callers still receive
    block-level output when the breaker is open.
    """
    return engine._rule_based_fallback(semantic_blocks)


# Import metrics tracking
try:
    from app.services.model_metrics import get_model_metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Model metrics unavailable")

# Import unified LLM service (LiteLLM-backed)
try:
    from app.services.llm_service import (
        generate as _llm_generate,
        LLM_NVIDIA, LLM_DEEPSEEK,
        LLMUnavailableError,
        LITELLM_AVAILABLE,
    )
    _LLM_SERVICE_AVAILABLE = True
except ImportError:
    _LLM_SERVICE_AVAILABLE = False
    LITELLM_AVAILABLE = False
    LLM_NVIDIA = settings.NVIDIA_MODEL
    LLM_DEEPSEEK = "ollama/deepseek-r1"
    logger.warning("llm_service not available - using legacy LangChain paths")

# LangChain Ollama (secondary fallback when litellm/direct clients are unavailable)
# Avoid importing langchain_ollama on Python 3.14+ because upstream still routes
# through pydantic-v1 shims that emit deprecation warnings.
if sys.version_info >= (3, 14):
    ChatOllama = None
    _CHAT_OLLAMA_AVAILABLE = False
else:
    try:
        from langchain_ollama import ChatOllama
        _CHAT_OLLAMA_AVAILABLE = True
    except ImportError:
        ChatOllama = None
        _CHAT_OLLAMA_AVAILABLE = False

class ReasoningEngine:
    """
    Orchestrates LLM reasoning to make pipeline decisions.
    Straddles:
    - Tier 1: NVIDIA NIM (Llama 3 70B) - Primary High Intelligence
    - Tier 2: Ollama (DeepSeek Coder/Mistral) - Fallback Local Intelligence
    - Tier 3: Heuristic Rules - Safety Net
    """

    _ALLOWED_SEMANTIC_TYPES = {
        "TITLE",
        "AUTHOR",
        "AFFILIATION",
        "ABSTRACT_HEADING",
        "ABSTRACT_BODY",
        "HEADING_1",
        "HEADING_2",
        "BODY",
        "FIGURE_CAPTION",
        "TABLE_CAPTION",
        "REFERENCES_HEADING",
        "REFERENCE_ENTRY",
    }
    _SEMANTIC_ALIASES = {
        "BODY_TEXT": "BODY",
        "PARAGRAPH": "BODY",
        "HEADING": "HEADING_1",
        "SECTION_HEADING": "HEADING_1",
        "REFERENCE": "REFERENCE_ENTRY",
        "BIBLIOGRAPHY_ENTRY": "REFERENCE_ENTRY",
        "BIBLIOGRAPHY_HEADING": "REFERENCES_HEADING",
    }
    
    def __init__(self, timeout: int = 30, model: Optional[str] = None):
        if timeout == 30:
            timeout = int(settings.PIPELINE_REASONING_TIMEOUT_SECONDS)

        in_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))
        if in_pytest:
            # Keep tests deterministic even when the developer machine has live API keys.
            self.nvidia_api_key = ""
            enable_nvidia = False
        else:
            self.nvidia_api_key = settings.NVIDIA_API_KEY or ""
            enable_nvidia = bool(settings.ENABLE_NVIDIA_REASONER)
        
        # Ollama Configuration
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.fallback_model = (model or "deepseek-r1:8b").strip()
        
        self.timeout = max(5, int(timeout))  # Supports ReasoningEngine(timeout=N)
        self.model = self.fallback_model
        
        # Initialize NVIDIA client (primary)
        self.nvidia_client = None
        self.nvidia_available = False
        if enable_nvidia:
            try:
                from app.services.nvidia_client import get_nvidia_client
                self.nvidia_client = get_nvidia_client()
                self.nvidia_available = self.nvidia_client is not None
                if self.nvidia_available:
                    logger.info("NVIDIA Llama 3.3 70B available (primary)")
            except Exception as e:
                logger.warning("NVIDIA unavailable: %s", e)
        else:
            logger.info("NVIDIA reasoning disabled for current environment.")
        
        # Initialize DeepSeek/Ollama (fallback)
        self.ollama_available = self._check_ollama_health()
        
        if self.ollama_available:
            try:
                self.llm = ChatOllama(
                    model=self.fallback_model,
                    base_url=self.ollama_base_url,
                    format="json",  # Ensure JSON output
                    timeout=self.timeout
                )
                logger.info("DeepSeek %s available (fallback)", self.fallback_model)
            except Exception as e:
                logger.warning("Failed to init ChatOllama: %s", e)
                self.llm = None
                self.ollama_available = False
        else:
            self.llm = None
            logger.info(
                "Ollama fallback unavailable at %s; continuing with NVIDIA/rule-based fallbacks.",
                self.ollama_base_url,
            )
        
        # Always have rule-based fallback
        logger.info("Rule-based heuristics available (final fallback)")
    
    def _check_ollama_health(self) -> bool:
        """Check if Ollama server is reachable and find best model."""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                try:
                    data = response.json()
                    if not isinstance(data, dict):
                        # Mock-friendly: non-dict json() means server is "up"
                        return True
                    models = data.get('models', [])
                    if not isinstance(models, list):
                        return True  # mock list-like
                    model_names = [m.get('name') for m in models if isinstance(m, dict)]
                except Exception:
                    return True  # Consider server reachable if json parse fails
                
                # Check if default exists
                if self.fallback_model in model_names:
                    return True
                
                # Find best alternative (prefer deepseek)
                for m in model_names:
                    if "deepseek" in m.lower():
                        logger.info("Auto-selected DeepSeek model: %s", m)
                        self.fallback_model = m
                        return True
                
                # Fallback to any model if deepseek not found
                if model_names:
                    logger.info("DeepSeek not found, using available model: %s", model_names[0])
                    self.fallback_model = model_names[0]
                    return True
                
                # 200 response but no models - still treat as available
                return True
            return False
        except (requests.RequestException, Exception):
            return False

    @staticmethod
    def _is_cancelled(cancellation_event: Any) -> bool:
        return bool(cancellation_event is not None and hasattr(cancellation_event, "is_set") and cancellation_event.is_set())
    
    def _validate_json_schema(self, data: Dict[str, Any]) -> bool:
        """Validate JSON output schema."""
        if not isinstance(data, dict):
            return False
        if "error" in data:
            return False
        blocks = data.get("blocks")
        if not isinstance(blocks, list):
            return False
        for block in blocks:
            if not isinstance(block, dict):
                return False

            block_id = block.get("block_id")
            semantic_type = block.get("semantic_type")
            confidence = block.get("confidence")

            if block_id is None:
                return False
            if not str(block_id).strip():
                return False
            if not isinstance(semantic_type, str) or not semantic_type.strip():
                return False
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                return False
            if confidence_value < 0.0 or confidence_value > 1.0:
                return False
        return True

    def _normalize_semantic_type(self, value: Any) -> str:
        """Normalize LLM semantic labels into the canonical instruction set."""
        if value is None:
            return "BODY"

        semantic = str(value).strip().upper().replace("-", "_").replace(" ", "_")
        semantic = self._SEMANTIC_ALIASES.get(semantic, semantic)

        if semantic in self._ALLOWED_SEMANTIC_TYPES:
            return semantic
        if "ABSTRACT" in semantic and "HEADING" in semantic:
            return "ABSTRACT_HEADING"
        if "ABSTRACT" in semantic:
            return "ABSTRACT_BODY"
        if "REFERENCE" in semantic or "BIBLIO" in semantic:
            return "REFERENCE_ENTRY"
        if semantic.startswith("HEADING"):
            return "HEADING_1"
        return "BODY"

    def _normalize_confidence(self, value: Any, default: float = 0.72) -> float:
        """Coerce confidence values to a bounded [0.0, 1.0] float."""
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return default
        if confidence < 0.0:
            return 0.0
        if confidence > 1.0:
            return 1.0
        return confidence

    def _normalize_instruction_payload(
        self,
        data: Optional[Dict[str, Any]],
        semantic_blocks: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize model output into canonical schema.
        Accepts variants like `instructions`/`blocks`, id aliases, and score aliases.
        """
        if not isinstance(data, dict):
            return None

        raw_blocks = data.get("blocks")
        if not isinstance(raw_blocks, list):
            alt_blocks = data.get("instructions")
            raw_blocks = alt_blocks if isinstance(alt_blocks, list) else None
        if not isinstance(raw_blocks, list):
            return None

        normalized_blocks: List[Dict[str, Any]] = []
        for idx, raw in enumerate(raw_blocks):
            if not isinstance(raw, dict):
                continue

            source = semantic_blocks[idx] if idx < len(semantic_blocks) else {}
            block_id = (
                raw.get("block_id")
                or raw.get("blockId")
                or raw.get("id")
                or source.get("block_id")
                or source.get("id")
                or f"b{idx}"
            )
            block_id = str(block_id).strip() or f"b{idx}"

            semantic_type = self._normalize_semantic_type(
                raw.get("semantic_type")
                or raw.get("type")
                or raw.get("label")
                or raw.get("section_type")
                or raw.get("classification")
            )
            confidence = self._normalize_confidence(
                raw.get("confidence")
                or raw.get("score")
                or raw.get("probability")
            )

            normalized: Dict[str, Any] = {
                "block_id": block_id,
                "semantic_type": semantic_type,
                "confidence": confidence,
            }

            canonical_section_name = raw.get("canonical_section_name") or raw.get("section_name")
            if isinstance(canonical_section_name, str) and canonical_section_name.strip():
                normalized["canonical_section_name"] = canonical_section_name.strip()

            normalized_blocks.append(normalized)

        if not normalized_blocks:
            return None

        avg_confidence = sum(block["confidence"] for block in normalized_blocks) / len(normalized_blocks)
        normalized_payload: Dict[str, Any] = {
            "blocks": normalized_blocks,
            "instructions": normalized_blocks,
            "confidence": round(avg_confidence, 3),
            "fallback": bool(data.get("fallback", False)),
        }

        model_name = data.get("model")
        if isinstance(model_name, str) and model_name.strip():
            normalized_payload["model"] = model_name.strip()

        latency = data.get("latency")
        if isinstance(latency, (int, float)):
            normalized_payload["latency"] = float(latency)

        return normalized_payload
    
    def _rule_based_fallback(self, semantic_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rule-based classification fallback when Ollama unavailable."""
        logger.warning("Using rule-based fallback classification")
        blocks = []
        for block in semantic_blocks:
            text = block.get("text", "").strip().lower()
            
            # Simple heuristic classification
            if len(text) < 50 and text.endswith(":"):
                semantic_type = "HEADING_1"
            elif "abstract" in text[:20]:
                semantic_type = "ABSTRACT_BODY"
            elif "introduction" in text[:20]:
                semantic_type = "HEADING_1"
            elif "reference" in text or "bibliography" in text:
                semantic_type = "REFERENCE_ENTRY"
            else:
                semantic_type = "BODY_TEXT"
            
            blocks.append({
                "block_id": block.get("block_id", f"b{block.get('index', 0)}"),
                "semantic_type": semantic_type,
                "canonical_section_name": text[:50] if len(text) < 50 else "Body",
                "confidence": 0.5  # Lower confidence for rule-based
            })
        
        return {
            "blocks": blocks,
            "instructions": blocks,
            "confidence": 0.5,
            "fallback": True,
        }
    
    @retry_guard(max_retries=3)
    def _call_ollama(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Local Ollama API (direct HTTP - used when llm_service unavailable)."""
        try:
            payload = {
                "model": self.fallback_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3, "num_predict": 2048},
            }
            response = requests.post(
                f"{self.ollama_base_url}/api/generate", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            llm_output_str = response.json().get("response", "")
            try:
                return json.loads(llm_output_str)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', llm_output_str, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except json.JSONDecodeError:
                        return None
                return None
        except requests.exceptions.RequestException as e:
            logger.warning("Ollama API call failed: %s", e)
            return None
        except Exception as e:
            logger.warning("Unexpected error during Ollama call: %s", e)
            return None

    @retry_guard(max_retries=2, base_delay=0.5)
    def _call_nvidia_litellm(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Call NVIDIA NIM via llm_service (LiteLLM-backed)."""
        if not _LLM_SERVICE_AVAILABLE or not self.nvidia_api_key:
            return None
        text = _llm_generate(
            messages=messages,
            model=LLM_NVIDIA,
            temperature=0.3,
            max_tokens=2048,
            timeout=self.timeout,
            api_key=self.nvidia_api_key,
        )
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        return None

    @guard_llm_output(schema=InstructionSetSchema, error_return_value={"blocks": [], "fallback": True})
    @circuit_breaker(
        failure_threshold=3,
        recovery_timeout=60,
        fallback_function=_instruction_set_circuit_fallback,
    )
    def generate_instruction_set(
        self,
        semantic_blocks: List[Dict[str, Any]],
        rules: str,
        max_retries: int = 2,
        cancellation_event: Any = None,
    ) -> Dict[str, Any]:
        """
        - Automatic fallback on failure
        - Retry logic for transient failures
        - JSON schema validation
        - Timeout protection
        """
        if self._is_cancelled(cancellation_event):
            logger.info("Reasoning cancelled before start; using rule-based fallback.")
            return self._rule_based_fallback(semantic_blocks)

        # Try NVIDIA first (if available)
        if getattr(self, 'nvidia_available', False) and getattr(self, 'nvidia_client', None):
            start_time = 0.0  # initialised before try so except can reference it safely
            try:
                if self._is_cancelled(cancellation_event):
                    logger.info("Reasoning cancelled before NVIDIA call; using rule-based fallback.")
                    return self._rule_based_fallback(semantic_blocks)
                logger.info("Attempting NVIDIA Llama 3.3 70B...")
                start_time = time.time()
                result = self._generate_with_nvidia(semantic_blocks, rules, cancellation_event=cancellation_event)
                result = self._normalize_instruction_payload(result, semantic_blocks)
                latency = time.time() - start_time
                
                if result and self._validate_json_schema(result):
                    result["latency"] = latency
                    result["model"] = "NVIDIA Llama 3.3 70B"
                    result["fallback"] = False
                    
                    # Record metrics
                    if METRICS_AVAILABLE:
                        get_model_metrics().record_call("nvidia", True, latency)
                    
                    logger.info("NVIDIA analysis successful (%.2fs)", latency)
                    return result
                else:
                    # Record failure
                    if METRICS_AVAILABLE:
                        get_model_metrics().record_call("nvidia", False, latency)
                        get_model_metrics().record_fallback("nvidia", "deepseek", "Invalid schema")
                    logger.warning("NVIDIA returned invalid schema or no result, falling back...")
            except Exception as e:
                # Record failure
                if METRICS_AVAILABLE:
                    get_model_metrics().record_call("nvidia", False, time.time() - start_time)
                    get_model_metrics().record_fallback("nvidia", "deepseek", str(e))
                logger.warning("NVIDIA failed: %s. Falling back to DeepSeek...", e)

        if self._is_cancelled(cancellation_event):
            logger.info("Reasoning cancelled before DeepSeek fallback; using rule-based fallback.")
            return self._rule_based_fallback(semantic_blocks)
        
        # Fallback to DeepSeek/Ollama
        if getattr(self, 'ollama_available', False) and getattr(self, 'llm', None) is not None:
            try:
                logger.info("Attempting DeepSeek via Ollama...")
                start_time = time.time()
                result = self._generate_with_deepseek(
                    semantic_blocks,
                    rules,
                    max_retries,
                    cancellation_event=cancellation_event,
                )
                result = self._normalize_instruction_payload(result, semantic_blocks)
                latency = time.time() - start_time

                if result and result.get("fallback"):
                    result["latency"] = latency
                    result["model"] = "rule_based"
                    if METRICS_AVAILABLE:
                        get_model_metrics().record_call("deepseek", False, latency)
                        get_model_metrics().record_fallback("deepseek", "rules", "DeepSeek returned fallback payload")
                    logger.warning("DeepSeek returned fallback payload; using normalized rule-based output.")
                    return result

                if result and self._validate_json_schema(result):
                    result["latency"] = latency
                    result["model"] = self.model
                    result["fallback"] = False
                    
                    # Record metrics
                    if METRICS_AVAILABLE:
                        get_model_metrics().record_call("deepseek", True, latency)
                    
                    logger.info("DeepSeek analysis successful (%.2fs)", latency)
                    return result
                else:
                    # Record failure
                    if METRICS_AVAILABLE:
                        get_model_metrics().record_call("deepseek", False, latency)
                        get_model_metrics().record_fallback("deepseek", "rules", "Invalid schema")
                    logger.warning("DeepSeek returned invalid schema or no result, falling back...")
            except Exception as e:
                # Record failure
                if METRICS_AVAILABLE:
                    get_model_metrics().record_call("deepseek", False, time.time() - start_time)
                    get_model_metrics().record_fallback("deepseek", "rules", str(e))
                logger.warning("DeepSeek failed: %s. Falling back to rules...", e)
        
        # Final fallback to rule-based
        logger.info("Using rule-based heuristics (final fallback)")
        return self._rule_based_fallback(semantic_blocks)
    
    def _generate_with_nvidia(
        self,
        semantic_blocks: List[Dict[str, Any]],
        rules: str,
        cancellation_event: Any = None,
    ) -> Dict[str, Any]:
        """Generate instruction set using NVIDIA Llama 3.3 70B (via llm_service when available)."""
        if self._is_cancelled(cancellation_event):
            return self._rule_based_fallback(semantic_blocks)

        if not semantic_blocks:
            return {"blocks": []}

        merged_blocks: List[Dict[str, Any]] = []
        for batch_start in range(0, len(semantic_blocks), MAX_BLOCKS_PER_CALL):
            batch = semantic_blocks[batch_start: batch_start + MAX_BLOCKS_PER_CALL]
            blocks_summary = []
            for i, b in enumerate(batch):
                global_index = batch_start + i
                text = b.get("text", "")[:150]
                hints = []
                if b.get("metadata", {}).get("heading_level"):
                    hints.append(f"H{b['metadata']['heading_level']}")
                if b.get("metadata", {}).get("is_code_block"):
                    hints.append(f"CODE({b['metadata']['code_language']})")
                if b.get("metadata", {}).get("is_table"):
                    hints.append("TABLE")
                if b.get("metadata", {}).get("is_list_item"):
                    hints.append("LIST_ITEM")
                if b.get("metadata", {}).get("font_size"):
                    hints.append(f"Size:{b['metadata']['font_size']:.1f}")
                if b.get("style", {}).get("bold"):
                    hints.append("BOLD")
                hint_str = f" [{', '.join(hints)}]" if hints else ""
                blocks_summary.append(f"Block {global_index}: {text}{hint_str}")

            system_prompt = (
                "You are an expert academic manuscript structure analyzer. "
                "Classify document blocks with HIGH CONFIDENCE.\n\n"
                "Available types: TITLE, AUTHOR, AFFILIATION, ABSTRACT_HEADING, ABSTRACT_BODY, "
                "HEADING_1, HEADING_2, BODY, FIGURE_CAPTION, TABLE_CAPTION, "
                "REFERENCES_HEADING, REFERENCE_ENTRY.\n\n"
                "Return ONLY valid JSON: {\"blocks\": [{\"block_id\": ..., "
                "\"semantic_type\": ..., \"confidence\": ...}]}"
            )
            user_prompt = (
                f"Classify all blocks:\n\n"
                f"{chr(10).join(blocks_summary)}\n\n"
                "Return JSON only."
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = ""
            if _LLM_SERVICE_AVAILABLE and LITELLM_AVAILABLE:
                try:
                    response = _llm_generate(
                        messages=messages,
                        model=LLM_NVIDIA,
                        temperature=0.3,
                        max_tokens=1536,
                        timeout=self.timeout,
                    )
                except Exception as exc:
                    logger.warning("llm_service NVIDIA call failed: %s", exc)

            if not response and self.nvidia_client:
                response = self.nvidia_client.chat(messages, model="llama-70b", temperature=0.3, max_tokens=2048)

            if not response:
                return None

            parsed = None
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError:
                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        parsed = None

            if not isinstance(parsed, dict):
                return None

            batch_blocks = parsed.get("blocks")
            if isinstance(batch_blocks, list):
                merged_blocks.extend(batch_blocks)

        return {"blocks": merged_blocks} if merged_blocks else None
    
    def _generate_with_deepseek(
        self,
        semantic_blocks: List[Dict[str, Any]],
        rules: str,
        max_retries: int,
        cancellation_event: Any = None,
    ) -> Dict[str, Any]:
        """Generate instruction set using DeepSeek via llm_service (LiteLLM) or direct Ollama."""
        def _parse_response(raw: str):  # type: Optional[Dict[str, Any]]
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                m = re.search(r'\{.*\}', raw, re.DOTALL)
                if m:
                    try:
                        return json.loads(m.group())
                    except json.JSONDecodeError:
                        pass
            return None

        merged_blocks: List[Dict[str, Any]] = []
        for batch_start in range(0, len(semantic_blocks), MAX_BLOCKS_PER_CALL):
            batch = semantic_blocks[batch_start: batch_start + MAX_BLOCKS_PER_CALL]
            blocks_json = json.dumps(batch)
            prompt = (
                f"Analyze these academic manuscript blocks and publisher guidelines.\n\n"
                f"MANUSCRIPT BLOCKS:\n{blocks_json}\n\n"
                f"PUBLISHER RULES (RAG):\n{rules}\n\n"
                "TASK: Generate a JSON 'Semantic Instruction Set'. "
                "For each block provide: block_id, semantic_type, canonical_section_name, confidence.\n"
                "OUTPUT JSON ONLY. Return format: {\"blocks\": [...]}"
            )
            messages = [{"role": "user", "content": prompt}]

            batch_result = None
            for attempt in range(max_retries + 1):
                if self._is_cancelled(cancellation_event):
                    logger.info("Reasoning cancelled during DeepSeek loop; using rule-based fallback.")
                    return self._rule_based_fallback(semantic_blocks)
                start_time = time.time()
                try:
                    if self.llm is not None:
                        response = self.llm.invoke(prompt)
                        batch_result = _parse_response(
                            response.content if hasattr(response, "content") else str(response)
                        )
                    elif _LLM_SERVICE_AVAILABLE and LITELLM_AVAILABLE:
                        raw = _llm_generate(
                            messages=messages,
                            model=LLM_DEEPSEEK,
                            temperature=0.3,
                            max_tokens=1536,
                            timeout=self.timeout,
                        )
                        batch_result = _parse_response(raw)
                    else:
                        batch_result = None

                    latency = time.time() - start_time
                    if batch_result:
                        logger.info("DeepSeek reasoning batch completed in %.2fs", latency)
                        break

                    logger.warning(
                        "DeepSeek returned unparseable response (attempt %d/%d)",
                        attempt + 1,
                        max_retries + 1,
                    )
                except json.JSONDecodeError as e:
                    logger.warning(
                        "DeepSeek JSON parse error (attempt %d/%d): %s",
                        attempt + 1,
                        max_retries + 1,
                        e,
                    )
                except Exception as e:
                    logger.warning(
                        "DeepSeek error (attempt %d/%d): %s",
                        attempt + 1,
                        max_retries + 1,
                        e,
                    )

                if attempt < max_retries:
                    if self._is_cancelled(cancellation_event):
                        return self._rule_based_fallback(semantic_blocks)
                    time.sleep(1)
                else:
                    logger.error("All retries failed for DeepSeek batch. Falling back to rule-based classification.")
                    return self._rule_based_fallback(semantic_blocks)

            if not isinstance(batch_result, dict):
                return self._rule_based_fallback(semantic_blocks)
            batch_blocks = batch_result.get("blocks") or batch_result.get("instructions")
            if isinstance(batch_blocks, list):
                merged_blocks.extend(batch_blocks)

        if not merged_blocks:
            return self._rule_based_fallback(semantic_blocks)
        return {"blocks": merged_blocks, "instructions": merged_blocks}

# Singleton Access
_reasoning_engine = None

def get_reasoning_engine() -> ReasoningEngine:
    global _reasoning_engine
    _reasoning_engine = get_or_create(_reasoning_engine, ReasoningEngine)
    return _reasoning_engine
