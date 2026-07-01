# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Application settings loaded from .env via pydantic-settings.

Policy:
- Do not hardcode runtime configuration in code.
- Read configuration from environment variables (via .env in local development).
- Settings are grouped into logical sub-configs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterable, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"
DEFAULT_LOCAL_CORS_ORIGINS = ",".join(
    (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
)

DEFAULT_GROBID_URL = "http://localhost:8070"
DEFAULT_GROBID_HEALTH_PATH = "/api/isalive"
DEFAULT_GENERIC_HEALTH_PATH = "/"


def _parse_boolish(value: Any, field_name: str) -> bool | Any:
    if isinstance(value, bool):
        return value
    if value is None:
        return value
    normalized = str(value).strip().lower()
    truthy = {"1", "true", "yes", "on", "debug", "development", "dev", "local"}
    falsy = {"0", "false", "no", "off", "release", "prod", "production"}
    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    logger.warning("Unexpected boolean value for %s=%r.", field_name, value)
    return value


def _normalize_cors_origins(value: Any) -> str:
    if value is None:
        # In production (DEBUG=false), don't default to localhost
        is_debug = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
        if not is_debug:
            return ""
        return DEFAULT_LOCAL_CORS_ORIGINS
    origins = [origin.strip() for origin in str(value).split(",") if origin.strip()]
    filtered = [origin for origin in origins if "<your-frontend-domain>" not in origin]
    if filtered:
        return ",".join(filtered)
    # In production, return empty if no valid origins provided
    is_debug = os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")
    if not is_debug:
        return ""
    return DEFAULT_LOCAL_CORS_ORIGINS


def _normalize_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized.rstrip("/")


def _split_urls(raw_value: str | None) -> list[str]:
    if raw_value is None:
        return []
    values = []
    for part in str(raw_value).split(","):
        normalized = _normalize_base_url(part)
        if normalized:
            values.append(normalized)
    return values


def _dedupe(values: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        deduped.append(value)
        seen.add(value)
    return deduped


def _resolve_service_urls(
    raw_urls_value: str | None,
    single_url_values: Iterable[str | None],
    *,
    default_urls: Iterable[str] = (),
) -> list[str]:
    urls = _split_urls(raw_urls_value)
    if urls:
        return _dedupe(urls)
    fallback_urls = [_normalize_base_url(value) for value in single_url_values]
    filtered_fallback_urls = [value for value in fallback_urls if value]
    if filtered_fallback_urls:
        return _dedupe(filtered_fallback_urls)
    return _dedupe([value for value in default_urls if value])


def _normalize_health_path(value: str | None, *, default_path: str) -> str:
    normalized = str(value or default_path).strip()
    if not normalized:
        normalized = default_path
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if len(normalized) > 1:
        normalized = normalized.rstrip("/")
    return normalized or default_path


class _ServiceUrlMixin:
    def get_grobid_urls(self) -> list[str]:
        return _resolve_service_urls(
            getattr(self, "GROBID_URLS", None),
            (
                getattr(self, "GROBID_URL", None),
                getattr(self, "GROBID_BASE_URL", None),
            ),
            default_urls=(DEFAULT_GROBID_URL,),
        )

    def get_docling_urls(self) -> list[str]:
        return _resolve_service_urls(
            getattr(self, "DOCLING_URLS", None),
            (getattr(self, "DOCLING_URL", None),),
        )

    def get_ocr_urls(self) -> list[str]:
        return _resolve_service_urls(
            getattr(self, "OCR_URLS", None),
            (getattr(self, "OCR_URL", None),),
        )

    def get_docx_converter_urls(self) -> list[str]:
        return _resolve_service_urls(
            getattr(self, "DOCX_CONVERTER_URLS", None),
            (getattr(self, "DOCX_CONVERTER_URL", None),),
        )

    def get_nougat_urls(self) -> list[str]:
        return _resolve_service_urls(
            getattr(self, "NOUGAT_URLS", None),
            (getattr(self, "NOUGAT_URL", None),),
        )

    def get_scibert_urls(self) -> list[str]:
        return _resolve_service_urls(
            getattr(self, "SCIBERT_URLS", None),
            (getattr(self, "SCIBERT_URL", None),),
        )

    def get_service_health_path(self, service_name: str) -> str:
        normalized_name = service_name.strip().lower()
        if normalized_name == "grobid":
            return _normalize_health_path(
                getattr(self, "GROBID_HEALTH_PATH", DEFAULT_GROBID_HEALTH_PATH),
                default_path=DEFAULT_GROBID_HEALTH_PATH,
            )
        if normalized_name == "docling":
            return _normalize_health_path(
                getattr(self, "DOCLING_HEALTH_PATH", DEFAULT_GENERIC_HEALTH_PATH),
                default_path=DEFAULT_GENERIC_HEALTH_PATH,
            )
        if normalized_name == "ocr":
            return _normalize_health_path(
                getattr(self, "OCR_HEALTH_PATH", DEFAULT_GENERIC_HEALTH_PATH),
                default_path=DEFAULT_GENERIC_HEALTH_PATH,
            )
        if normalized_name == "docx_converter":
            return _normalize_health_path(
                getattr(self, "DOCX_CONVERTER_HEALTH_PATH", DEFAULT_GENERIC_HEALTH_PATH),
                default_path=DEFAULT_GENERIC_HEALTH_PATH,
            )
        if normalized_name == "nougat":
            return _normalize_health_path(
                getattr(self, "NOUGAT_HEALTH_PATH", DEFAULT_GENERIC_HEALTH_PATH),
                default_path=DEFAULT_GENERIC_HEALTH_PATH,
            )
        if normalized_name == "scibert":
            return _normalize_health_path(
                getattr(self, "SCIBERT_HEALTH_PATH", DEFAULT_GENERIC_HEALTH_PATH),
                default_path=DEFAULT_GENERIC_HEALTH_PATH,
            )
        raise ValueError(f"Unknown service_name: {service_name!r}")


class DatabaseSettings(_ServiceUrlMixin, BaseSettings):
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_JWKS_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_DB_URL: Optional[str] = None

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


class LLMSettings(BaseSettings):
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = ""
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = ""
    GROQ_API_BASE: str = ""
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_API_BASE: str = "https://openrouter.ai/api/v1"
    GOOGLE_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    OLLAMA_URL: str = ""
    OLLAMA_BASE_URL: str = ""
    LLM_PROVIDER_TIMEOUT_SECONDS: int = 15

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


class PipelineSettings(_ServiceUrlMixin, BaseSettings):
    GROBID_URL: str = DEFAULT_GROBID_URL
    GROBID_BASE_URL: str = DEFAULT_GROBID_URL
    GROBID_URLS: str = ""
    GROBID_HEALTH_PATH: str = DEFAULT_GROBID_HEALTH_PATH
    GROBID_TIMEOUT: int = 10
    GROBID_MAX_RETRIES: int = 3
    GROBID_ENABLED: bool = True
    USE_DOCLING_FALLBACK: bool = True
    PYMUPDF_FALLBACK: bool = True

    DOCLING_URL: Optional[str] = None
    DOCLING_URLS: str = ""
    DOCLING_HEALTH_PATH: str = DEFAULT_GENERIC_HEALTH_PATH
    OCR_URL: Optional[str] = None
    OCR_URLS: str = ""
    OCR_HEALTH_PATH: str = DEFAULT_GENERIC_HEALTH_PATH
    DOCX_CONVERTER_URL: Optional[str] = None
    DOCX_CONVERTER_URLS: str = ""
    DOCX_CONVERTER_HEALTH_PATH: str = DEFAULT_GENERIC_HEALTH_PATH
    NOUGAT_URL: Optional[str] = None
    NOUGAT_URLS: str = ""
    NOUGAT_HEALTH_PATH: str = DEFAULT_GENERIC_HEALTH_PATH
    SCIBERT_URL: Optional[str] = None
    SCIBERT_URLS: str = ""
    SCIBERT_HEALTH_PATH: str = DEFAULT_GENERIC_HEALTH_PATH

    PIPELINE_GROBID_TIMEOUT_SECONDS: int = 30
    PIPELINE_DOCLING_TIMEOUT_SECONDS: int = 30
    PIPELINE_REASONING_TIMEOUT_SECONDS: int = 60
    PIPELINE_SEMANTIC_TIMEOUT_SECONDS: int = 30
    PIPELINE_ACQUIRE_TIMEOUT_SECONDS: float = 30.0
    PIPELINE_DOCLING_SKIP_DIGITAL_PDF: bool = False
    PIPELINE_DOCLING_FORCE: bool = False
    ENABLE_NOUGAT_PARSER: bool = False
    ENABLE_NVIDIA_REASONER: bool = False
    USE_SCIBERT_CLASSIFICATION: bool = False
    SCIBERT_AUTO_ENABLE_FROM_BENCHMARK: bool = True
    SCIBERT_MIN_BENCHMARK_F1: float = 0.85
    SCIBERT_BENCHMARK_STATE_PATH: str = ".metrics/scibert_benchmark_state.json"
    PRELOAD_AI_MODELS: bool = True
    LOW_MEMORY_MODE: bool = False
    RAG_USE_TRANSFORMERS: bool = True
    DEFAULT_FAST_MODE: bool = False

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator(
        "GROBID_ENABLED",
        "USE_DOCLING_FALLBACK",
        "PYMUPDF_FALLBACK",
        "PIPELINE_DOCLING_SKIP_DIGITAL_PDF",
        "PIPELINE_DOCLING_FORCE",
        "ENABLE_NOUGAT_PARSER",
        "ENABLE_NVIDIA_REASONER",
        "USE_SCIBERT_CLASSIFICATION",
        "SCIBERT_AUTO_ENABLE_FROM_BENCHMARK",
        "LOW_MEMORY_MODE",
        "PRELOAD_AI_MODELS",
        "RAG_USE_TRANSFORMERS",
        "DEFAULT_FAST_MODE",
        mode="before",
    )
    @classmethod
    def parse_bool_fields(cls, value: Any, info) -> Any:
        return _parse_boolish(value, info.field_name)


class SecuritySettings(BaseSettings):
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: str = DEFAULT_LOCAL_CORS_ORIGINS
    SIGNED_URL_SECRET: Optional[str] = None
    FORCE_HTTPS: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    SENTRY_DSN: Optional[str] = None

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator("FORCE_HTTPS", mode="before")
    @classmethod
    def parse_bool_fields(cls, value: Any, info) -> Any:
        return _parse_boolish(value, info.field_name)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: Any) -> str:
        return _normalize_cors_origins(value)


class CacheSettings(BaseSettings):
    REDIS_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    LLM_CACHE_TTL_SECONDS: int = 3600
    READINESS_CACHE_TTL_SECONDS: int = 15
    HEALTH_CACHE_TTL_SECONDS: int = 15
    CSL_SEARCH_CACHE_TTL_SECONDS: int = 300
    CSL_FETCH_CACHE_TTL_SECONDS: int = 1800
    GENERATOR_SESSION_CACHE_TTL_SECONDS: float = 2.0
    GENERATOR_MESSAGES_CACHE_TTL_SECONDS: float = 1.0
    GENERATOR_SESSION_LIST_CACHE_TTL_SECONDS: float = 3.0
    GENERATOR_DOCUMENT_CACHE_TTL_SECONDS: float = 2.0
    DOCUMENT_STATUS_CACHE_TTL_SECONDS: float = 1.0

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator("REDIS_ENABLED", mode="before")
    @classmethod
    def parse_bool_fields(cls, value: Any, info) -> Any:
        return _parse_boolish(value, info.field_name)


class DeploymentSettings(BaseSettings):
    DEBUG: bool = False
    ENABLE_STRUCTURED_LOGGING: bool = False
    GLOBAL_RATE_LIMIT_PER_MINUTE: int = 120
    MAX_FILE_SIZE: int = 60 * 1024 * 1024
    MAX_BATCH_FILES: int = 10
    UPLOADS_PER_MINUTE: int = 10
    ENABLE_FILE_CLEANUP: bool = True
    RETENTION_DAYS: int = 30
    GENERATED_OUTPUT_DIR: str = "output"
    DEFAULT_TEMPLATE: str = "ieee"
    CROSSREF_MAILTO: str = "dev@example.com"
    LIBREOFFICE_PATH: Optional[str] = None

    EXTERNAL_CIRCUIT_BREAKER_ENABLED: bool = True
    EXTERNAL_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 3
    EXTERNAL_CIRCUIT_BREAKER_RESET_SECONDS: int = 60

    VLLM_ADOPTION_ENABLED: bool = True
    VLLM_TARGET_MODEL: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    VLLM_TARGET_GPU: str = "L4 24GB"
    VLLM_REQUESTS_PER_HOUR_THRESHOLD: int = 2000
    VLLM_DAILY_TOKENS_THRESHOLD: int = 5000000

    ENHANCEMENTS_ENABLED: bool = True
    ENHANCEMENT_QUEUE_ENABLED: bool = False
    ENHANCEMENT_QUEUE_PROVIDER: str = "auto"
    ENHANCEMENT_OCR_ENABLED: bool = True
    ENHANCEMENT_OCR_BACKENDS: str = "tesseract,paddle,surya"
    ENHANCEMENT_KEYWORD_ENABLED: bool = True
    ENHANCEMENT_KEYWORD_BACKENDS: str = "keyllm,keybert,yake,basic"
    ENHANCEMENT_QUEUE_MIN_SECONDS: float = 5.0
    CROSSREF_MAX_WORKERS: int = 4

    HEADING_STYLE_THRESHOLD: float = 0.8
    HEADING_FALLBACK_CONFIDENCE: float = 0.5
    HEURISTIC_CONFIDENCE_HIGH: float = 0.9
    HEURISTIC_CONFIDENCE_MEDIUM: float = 0.7
    HEURISTIC_CONFIDENCE_LOW: float = 0.4

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @field_validator(
        "DEBUG",
        "ENABLE_STRUCTURED_LOGGING",
        "ENABLE_FILE_CLEANUP",
        "EXTERNAL_CIRCUIT_BREAKER_ENABLED",
        "VLLM_ADOPTION_ENABLED",
        "ENHANCEMENTS_ENABLED",
        "ENHANCEMENT_QUEUE_ENABLED",
        "ENHANCEMENT_OCR_ENABLED",
        "ENHANCEMENT_KEYWORD_ENABLED",
        mode="before",
    )
    @classmethod
    def parse_bool_fields(cls, value: Any, info) -> Any:
        return _parse_boolish(value, info.field_name)

    @field_validator(
        "HEADING_STYLE_THRESHOLD",
        "HEADING_FALLBACK_CONFIDENCE",
        "HEURISTIC_CONFIDENCE_HIGH",
        "HEURISTIC_CONFIDENCE_MEDIUM",
        "HEURISTIC_CONFIDENCE_LOW",
        mode="before",
    )
    @classmethod
    def clamp_confidence(cls, value: Any) -> float:
        fv = float(value)
        if not (0.0 <= fv <= 1.0):
            logger.warning("Confidence value %s outside [0,1]. Clamping.", fv)
            return max(0.0, min(1.0, fv))
        return fv


class Settings(_ServiceUrlMixin):
    """Unified application settings composed from logical sub-configs."""

    def __init__(self) -> None:
        self.database = DatabaseSettings()
        self.llm = LLMSettings()
        self.pipeline = PipelineSettings()
        self.security = SecuritySettings()
        self.cache = CacheSettings()
        self.deployment = DeploymentSettings()

        self._sync_attributes()
        self.validate()

    def _sync_attributes(self) -> None:
        for section in (self.database, self.llm, self.pipeline, self.security, self.cache, self.deployment):
            for key, value in section.model_dump().items():
                object.__setattr__(self, key, value)

    def validate(self) -> None:
        for name in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_JWT_SECRET", "SUPABASE_SERVICE_ROLE_KEY"):
            if not getattr(self, name, None):
                logger.warning("%s is not set. DB/auth endpoints will fail at request time.", name)

        grobid_urls = self.get_grobid_urls()
        if grobid_urls:
            self.GROBID_URL = grobid_urls[0]
            self.GROBID_BASE_URL = grobid_urls[0]
        else:
            self.GROBID_URL = DEFAULT_GROBID_URL
            self.GROBID_BASE_URL = DEFAULT_GROBID_URL

        self.GROBID_HEALTH_PATH = self.get_service_health_path("grobid")
        self.DOCLING_HEALTH_PATH = self.get_service_health_path("docling")
        self.OCR_HEALTH_PATH = self.get_service_health_path("ocr")
        self.DOCX_CONVERTER_HEALTH_PATH = self.get_service_health_path("docx_converter")
        self.NOUGAT_HEALTH_PATH = self.get_service_health_path("nougat")
        self.SCIBERT_HEALTH_PATH = self.get_service_health_path("scibert")

        if self.RETENTION_DAYS <= 0:
            raise ValueError("RETENTION_DAYS must be > 0")

    def get_grobid_urls(self) -> list[str]:
        return self.pipeline.get_grobid_urls()

    def get_docling_urls(self) -> list[str]:
        return self.pipeline.get_docling_urls()

    def get_ocr_urls(self) -> list[str]:
        return self.pipeline.get_ocr_urls()

    def get_docx_converter_urls(self) -> list[str]:
        return self.pipeline.get_docx_converter_urls()

    def get_nougat_urls(self) -> list[str]:
        return self.pipeline.get_nougat_urls()

    def get_scibert_urls(self) -> list[str]:
        return self.pipeline.get_scibert_urls()

    def get_service_health_path(self, service_name: str) -> str:
        return self.pipeline.get_service_health_path(service_name)


settings = Settings()
