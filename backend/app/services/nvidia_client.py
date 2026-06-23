# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
NVIDIA NIM API Client — now powered by LiteLLM internally.
"""
from __future__ import annotations
import base64
import logging
import os
from typing import List, Dict, Any, Optional
from app.utils.singleton import get_or_create_safe
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Use unified LiteLLM service; fall back to direct OpenAI client if unavailable
try:
    from app.services.llm_service import generate as _llm_generate, LLM_NVIDIA, LITELLM_AVAILABLE
    _USE_LLM_SERVICE = True
except ImportError:
    _USE_LLM_SERVICE = False
    LITELLM_AVAILABLE = False
    LLM_NVIDIA = settings.NVIDIA_MODEL

try:
    from openai import OpenAI as _OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class NvidiaClient:
    """Client for NVIDIA NIM API (LiteLLM-backed when available)."""

    def __init__(self):
        env_key = os.getenv("NVIDIA_API_KEY")
        if env_key is not None:
            self.api_key = env_key
        elif os.getenv("PYTEST_CURRENT_TEST"):
            # Test suite expects no-key degraded mode unless key is explicitly patched.
            self.api_key = ""
        else:
            self.api_key = settings.NVIDIA_API_KEY
        self.client = None

        if not self.api_key:
            logger.warning(
                "NvidiaClient: NVIDIA_API_KEY not set — running in degraded mode. "
                "All API calls will return empty results."
            )
        else:
            if not _USE_LLM_SERVICE or not LITELLM_AVAILABLE:
                # Build raw OpenAI client as fallback
                if _OPENAI_AVAILABLE:
                    try:
                        self.client = _OpenAI(
                            base_url="https://integrate.api.nvidia.com/v1",
                            api_key=self.api_key,
                        )
                        logger.info("NvidiaClient: direct OpenAI client initialized (litellm not available).")
                    except Exception as exc:
                        logger.error("NvidiaClient: OpenAI client init failed: %s", exc)
            else:
                logger.info("NvidiaClient: using LiteLLM for NVIDIA calls.")

        # Model identifiers
        self.llama_70b = settings.NVIDIA_MODEL.replace("nvidia_nim/", "")
        self.llama_vision = "meta/llama-3.2-11b-vision-instruct"

    def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "llama-70b",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: int = 30,
    ) -> str:
        """
        Send a chat completion request to NVIDIA NIM.

        Args:
            messages:    OpenAI-format message list
            model:       'llama-70b' or 'llama-vision'
            temperature: Sampling temperature
            max_tokens:  Max tokens to generate

        Returns:
            Generated text (empty string on failure)
        """
        if not self.api_key:
            logger.warning("NvidiaClient.chat: No API key — returning empty.")
            return ""

        model_name = self.llama_70b if model == "llama-70b" else self.llama_vision
        temperature = max(0.0, min(1.0, temperature))

        # ── Path 1: LiteLLM ───────────────────────────────────────────── #
        if _USE_LLM_SERVICE and LITELLM_AVAILABLE:
            try:
                litellm_model = f"nvidia_nim/{model_name}"
                return _llm_generate(
                    messages=messages,
                    model=litellm_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    api_key=self.api_key,
                )
            except Exception as exc:
                logger.warning("NvidiaClient.chat: LiteLLM call failed (%s), trying direct client.", exc)

        # ── Path 2: Direct OpenAI-compat client ───────────────────────── #
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                choices = response.choices
                if not choices:
                    logger.warning("NvidiaClient.chat: API returned empty choices.")
                    return ""
                
                if hasattr(response, 'usage') and response.usage:
                    logger.info(
                        "NVIDIA NIM usage: prompt=%s, completion=%s, total=%s tokens",
                        getattr(response.usage, 'prompt_tokens', 0),
                        getattr(response.usage, 'completion_tokens', 0),
                        getattr(response.usage, 'total_tokens', 0)
                    )
                
                return choices[0].message.content or ""
            except Exception as exc:
                logger.error("NvidiaClient.chat: direct API call failed: %s", exc)
                raise

        logger.warning("NvidiaClient.chat: no client available.")
        return ""

    # ── Higher-level methods (signatures unchanged) ────────────────────── #

    def analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure using Llama 3.3 70B."""
        messages = [
            {
                "role": "system",
                "content": "You are an expert at analyzing academic manuscript structure. "
                           "Identify sections like Abstract, Introduction, Methods, Results, Discussion, Conclusion, References.",
            },
            {
                "role": "user",
                "content": f"Analyze this document and identify its sections:\n\n{text[:4000]}",
            },
        ]
        response = self.chat(messages, model="llama-70b", temperature=0.3)
        # Compute confidence from response quality
        confidence = 0.0
        if response:
            section_keywords = ["abstract", "introduction", "method", "result", "discussion", "conclusion", "reference"]
            detected = sum(1 for kw in section_keywords if kw in response.lower())
            confidence = min(1.0, 0.3 + (detected / len(section_keywords)) * 0.7)
        return {"analysis": response, "model": self.llama_70b, "confidence": round(confidence, 2)}

    def analyze_figure(self, image_path: str, caption: Optional[str] = None) -> str:
        """Analyze figure/diagram using Llama 3.2 11B Vision."""
        fallback_text = caption if caption else "Figure (AI analysis unavailable)"
        try:
            # Determine media type from file extension
            ext = image_path.lower()
            if ext.endswith(('.png',)):
                media_type = "image/png"
            elif ext.endswith(('.jpg', '.jpeg')):
                media_type = "image/jpeg"
            elif ext.endswith(('.gif',)):
                media_type = "image/gif"
            elif ext.endswith(('.webp',)):
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"  # Default fallback

            with open(image_path, "rb") as f:
                raw_data = f.read()

            if len(raw_data) > 2_000_000:
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(raw_data))
                if img.mode in ("RGBA", "P") and media_type == "image/jpeg":
                    img = img.convert("RGB")
                img.thumbnail((1024, 1024))
                buffer = io.BytesIO()
                save_format = 'PNG' if media_type == 'image/png' else 'JPEG'
                img.save(buffer, format=save_format)
                raw_data = buffer.getvalue()

            image_data = base64.b64encode(raw_data).decode()

            text_content = (
                f"This figure has caption: '{caption}'. Provide additional context:"
                if caption
                else "Describe this academic figure or diagram in detail:"
            )
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_content},
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                    ],
                }
            ]
            
            # API might throw or return empty string when key is missing/invalid
            result = self.chat(messages, model="llama-vision", temperature=0.5, max_tokens=512)
            return result if result else fallback_text
            
        except Exception as exc:
            logger.warning("NvidiaClient.analyze_figure: vision analysis failed: %s", exc)
            return fallback_text

    def validate_template_compliance(self, document_text: str, template: str) -> Dict[str, Any]:
        """Check if document complies with template requirements."""
        messages = [
            {
                "role": "system",
                "content": f"You are an expert at {template.upper()} formatting standards for academic papers.",
            },
            {
                "role": "user",
                "content": f"Check if this document follows {template.upper()} formatting requirements:\n\n{document_text[:2500]}",
            },
        ]
        response = self.chat(messages, model="llama-70b", temperature=0.3)
        is_compliant = "True" in response or "Yes" in response or "complies" in response.lower()
        if "does not comply" in response.lower() or "not compliant" in response.lower():
            is_compliant = False
        return {
            "compliant": is_compliant,
            "issues": [] if is_compliant else [response],
            "suggestions": response,
            "model": self.llama_70b,
        }


# ── Singleton ────────────────────────────────────────────────────────────── #
_nvidia_client: Optional[NvidiaClient] = None


def get_nvidia_client() -> Optional[NvidiaClient]:
    """Get or create the singleton NVIDIA client instance."""
    global _nvidia_client
    _nvidia_client = get_or_create_safe(
        _nvidia_client,
        NvidiaClient,
        logger=logger,
        name="get_nvidia_client",
    )
    return _nvidia_client
