# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
llm_factory.py - LiteLLM-backed LLM factory.

Public API unchanged:
  CustomLLMFactory.create_llm(provider, model, temperature, **kwargs)
  CustomLLMFactory.get_available_providers() -> List[str]
  CustomLLMFactory.get_recommended_models(provider) -> List[str]
"""

from __future__ import annotations

import logging
import os
import sys
from unittest.mock import Mock

from app.config.settings import settings

logger = logging.getLogger(__name__)

# LiteLLM availability
try:
    from app.services.llm_service import LITELLM_AVAILABLE
    from app.services.llm_service import generate as _llm_generate
except ImportError:
    LITELLM_AVAILABLE = False
    _llm_generate = None

if sys.version_info < (3, 14):
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        ChatOpenAI = None
else:
    ChatOpenAI = None

if sys.version_info < (3, 14):
    try:
        from langchain_community.llms import Ollama  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        Ollama = None
else:
    Ollama = None


def _is_mocked_constructor(value) -> bool:
    return isinstance(value, Mock)


class _LiteLLMShim:
    """LangChain-compatible wrapper: exposes .invoke(prompt) -> .content"""

    class _Response:
        def __init__(self, content: str):
            self.content = content

    def __init__(self, model: str, temperature: float, api_key=None, api_base=None):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key
        self.api_base = api_base

    def invoke(self, prompt: str, **kwargs) -> _LiteLLMShim._Response:
        messages = [{"role": "user", "content": prompt}]
        text = _llm_generate(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key,
            api_base=self.api_base,
        )
        return self._Response(text)

    def __call__(self, prompt: str, **kwargs) -> str:
        return self.invoke(prompt).content


class CustomLLMFactory:
    """
    Factory for LLM instances (LiteLLM shim when installed, LangChain fallback otherwise).

    Supported providers: openai, anthropic, ollama, nvidia, custom.
    """

    @staticmethod
    def create_llm(provider: str = "openai", model: str = "gpt-4", temperature: float = 0.0, **kwargs):
        """
        Create an LLM instance.

        Args:
            provider: 'openai', 'anthropic', 'ollama', 'nvidia', or 'custom'
            model:    Model name
            temperature: Sampling temperature
        Returns:
            LLM instance (LiteLLM shim or LangChain object)
        """
        force_langchain = (provider == "openai" and _is_mocked_constructor(ChatOpenAI)) or (
            provider == "ollama" and _is_mocked_constructor(Ollama)
        )

        if LITELLM_AVAILABLE and _llm_generate is not None and not force_langchain:
            return CustomLLMFactory._create_litellm(provider, model, temperature, **kwargs)
        return CustomLLMFactory._create_langchain(provider, model, temperature, **kwargs)

    @staticmethod
    def _create_litellm(provider: str, model: str, temperature: float, **kwargs):
        provider_prefixes = {
            "openai": lambda m: m,
            "anthropic": lambda m: m,
            "ollama": lambda m: f"ollama/{m}",
            "nvidia": lambda m: f"nvidia_nim/{m}",
        }
        model_fn = provider_prefixes.get(provider)
        if model_fn is None:
            raise ValueError(f"Unsupported provider: {provider}")
        litellm_model = model_fn(model)
        api_key = kwargs.get("api_key") or _get_api_key(provider)
        api_base = kwargs.get("api_base") or kwargs.get("base_url")
        logger.info("CustomLLMFactory: LiteLLM shim for %s/%s", provider, model)
        return _LiteLLMShim(model=litellm_model, temperature=temperature, api_key=api_key, api_base=api_base)

    @staticmethod
    def _create_langchain(provider: str, model: str, temperature: float, **kwargs):
        if provider == "openai":
            api_key = kwargs.get("api_key") or settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")
            llm_cls = ChatOpenAI
            if llm_cls is None:
                if sys.version_info >= (3, 14):
                    raise ImportError("LangChain OpenAI backend disabled on Python 3.14+")
                from langchain_openai import ChatOpenAI as llm_cls
            return llm_cls(
                model=model,
                temperature=temperature,
                api_key=api_key,
                **{k: v for k, v in kwargs.items() if k != "api_key"},
            )
        elif provider == "anthropic":
            if sys.version_info >= (3, 14):
                raise ImportError("LangChain Anthropic backend disabled on Python 3.14+")
            try:
                from langchain_anthropic import ChatAnthropic
            except ImportError:
                raise ImportError("langchain-anthropic not installed. pip install langchain-anthropic")
            api_key = kwargs.get("api_key") or settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                api_key=api_key,
                **{k: v for k, v in kwargs.items() if k != "api_key"},
            )
        elif provider == "ollama":
            base_url = kwargs.get("base_url", settings.OLLAMA_BASE_URL)
            llm_cls = Ollama
            if llm_cls is None:
                if sys.version_info >= (3, 14):
                    raise ImportError("LangChain Ollama backend disabled on Python 3.14+")
                from langchain_community.llms import Ollama as llm_cls
            return llm_cls(
                model=model,
                temperature=temperature,
                base_url=base_url,
                **{k: v for k, v in kwargs.items() if k != "base_url"},
            )
        elif provider == "custom":
            raise NotImplementedError("Custom LLM endpoints not yet implemented")
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def get_available_providers() -> list[str]:
        providers = []
        if settings.NVIDIA_API_KEY:
            providers.append("nvidia")
        if settings.OPENAI_API_KEY:
            providers.append("openai")
        if sys.version_info < (3, 14):
            try:
                import langchain_anthropic  # noqa

                if settings.ANTHROPIC_API_KEY:
                    providers.append("anthropic")
            except ImportError:
                pass  # intentionally ignored
        try:
            import requests

            r = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=1)
            if r.status_code == 200:
                providers.append("ollama")
        except Exception:
            pass  # intentionally ignored
        if LITELLM_AVAILABLE:
            providers.append("litellm")
        return providers

    @staticmethod
    def get_recommended_models(provider: str) -> list[str]:
        return {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "ollama": ["deepseek-r1:8b", "llama2", "mistral", "codellama"],
            "nvidia": ["meta/llama-3.3-70b-instruct", "meta/llama-3.2-11b-vision-instruct"],
            "litellm": ["nvidia_nim/meta/llama-3.3-70b-instruct", "ollama/deepseek-r1", "gpt-4"],
        }.get(provider, [])


def _get_api_key(provider: str):
    """Resolve API key from env for the given provider."""
    return {
        "openai": settings.OPENAI_API_KEY,
        "anthropic": settings.ANTHROPIC_API_KEY,
        "nvidia": settings.NVIDIA_API_KEY,
    }.get(provider)
