# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from app.config.settings import settings
from app.services.scibert_gate import get_scibert_gate_state, should_enable_scibert

logger = logging.getLogger(__name__)


_readiness_cache_lock: asyncio.Lock | None = None
_readiness_cache_payload: dict[str, Any] | None = None
_readiness_cache_status_code: int = 503
_readiness_cache_expiry: float = 0.0

_health_cache_lock: asyncio.Lock | None = None
_health_cache_payload: dict[str, Any] | None = None
_health_cache_status_code: int = 503
_health_cache_expiry: float = 0.0


def _get_readiness_cache_lock() -> asyncio.Lock:
    global _readiness_cache_lock
    if _readiness_cache_lock is None:
        _readiness_cache_lock = asyncio.Lock()
    return _readiness_cache_lock


def _get_health_cache_lock() -> asyncio.Lock:
    global _health_cache_lock
    if _health_cache_lock is None:
        _health_cache_lock = asyncio.Lock()
    return _health_cache_lock


def _readiness_ttl_seconds() -> float:
    raw_ttl = getattr(settings, "READINESS_CACHE_TTL_SECONDS", 15)
    try:
        ttl = float(raw_ttl)
    except (TypeError, ValueError):
        ttl = 15.0
    return max(0.0, ttl)


def _health_ttl_seconds() -> float:
    raw_ttl = getattr(settings, "HEALTH_CACHE_TTL_SECONDS", 15)
    try:
        ttl = float(raw_ttl)
    except (TypeError, ValueError):
        ttl = 15.0
    return max(0.0, ttl)


def _clone_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cloned = dict(payload)
    checks = cloned.get("checks")
    if isinstance(checks, dict):
        cloned["checks"] = dict(checks)
    dependencies = cloned.get("dependencies")
    if isinstance(dependencies, dict):
        cloned["dependencies"] = dict(dependencies)
    return cloned


def invalidate_readiness_cache() -> None:
    global _readiness_cache_payload, _readiness_cache_status_code, _readiness_cache_expiry
    _readiness_cache_payload = None
    _readiness_cache_status_code = 503
    _readiness_cache_expiry = 0.0


def invalidate_health_cache() -> None:
    global _health_cache_payload, _health_cache_status_code, _health_cache_expiry
    _health_cache_payload = None
    _health_cache_status_code = 503
    _health_cache_expiry = 0.0


def _reset_readiness_cache_for_tests() -> None:
    """Test helper to clear cached readiness state across test cases."""
    global _readiness_cache_lock, _health_cache_lock
    invalidate_readiness_cache()
    invalidate_health_cache()
    _readiness_cache_lock = None
    _health_cache_lock = None


def _service_urls(setting_method_name: str) -> list[str]:
    resolver = getattr(settings, setting_method_name, None)
    if callable(resolver):
        try:
            resolved = resolver()
        except Exception as e:
            logger.warning("Failed to resolve URLs for %s: %s", setting_method_name, e)
            resolved = []
        if isinstance(resolved, list):
            return [str(url).rstrip("/") for url in resolved if str(url).strip()]
    return []


def _service_health_path(service_name: str) -> str:
    try:
        path = settings.get_service_health_path(service_name)
    except (ValueError, Exception) as e:
        logger.warning("Failed to resolve health path for %s: %s", service_name, e)
        path = "/"
    return path


def _join_endpoint(base_url: str, health_path: str) -> str:
    return f"{base_url.rstrip('/')}{health_path}"


async def _probe_service_targets(
    *,
    service_name: str,
    urls: list[str],
    health_path: str,
    timeout_seconds: float = 2.0,
) -> dict[str, Any]:
    import httpx

    checked_at = datetime.now(timezone.utc).isoformat()
    if not urls:
        return {
            "service": service_name,
            "status": "unconfigured",
            "checked_at": checked_at,
            "last_probe": {
                "endpoint": None,
                "http_status": None,
                "error": "no_urls_configured",
            },
        }

    attempts: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        for base_url in urls:
            endpoint = _join_endpoint(base_url, health_path)
            try:
                response = await client.get(endpoint)
                attempt_payload = {
                    "endpoint": endpoint,
                    "http_status": response.status_code,
                    "error": None,
                }
                attempts.append(attempt_payload)
                if response.status_code == 200:
                    return {
                        "service": service_name,
                        "status": "ready",
                        "endpoint": endpoint,
                        "checked_at": checked_at,
                        "last_probe": attempt_payload,
                        "attempts": attempts,
                    }
            except Exception as exc:
                attempts.append(
                    {
                        "endpoint": endpoint,
                        "http_status": None,
                        "error": str(exc),
                    }
                )

    return {
        "service": service_name,
        "status": "unavailable",
        "endpoint": attempts[-1]["endpoint"] if attempts else None,
        "checked_at": checked_at,
        "last_probe": attempts[-1] if attempts else {"endpoint": None, "http_status": None, "error": "unknown"},
        "attempts": attempts,
    }


async def _build_health_payload() -> tuple[dict, int]:
    import httpx

    from app.db.supabase_client import check_supabase_health
    from app.services.model_store import model_store

    health_status: dict[str, Any] = {
        "status": "healthy",
        "version": "1.0.0",
        "components": {},
    }

    try:
        sb_health = check_supabase_health()
        health_status["components"]["supabase_db"] = sb_health.get("status", "unknown")
        if sb_health.get("status") != "healthy":
            health_status["status"] = "degraded"
    except Exception as exc:
        health_status["components"]["supabase_db"] = f"unhealthy: {str(exc)}"
        health_status["status"] = "degraded"

    ollama_url = getattr(settings, "OLLAMA_URL", "") or getattr(settings, "OLLAMA_BASE_URL", "")
    if ollama_url:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{ollama_url}/api/tags")
                if response.status_code == 200:
                    health_status["components"]["ollama"] = "healthy"
                else:
                    health_status["components"]["ollama"] = "unhealthy"
                    health_status["status"] = "degraded"
        except httpx.RequestError as exc:
            logger.warning("Ollama health check request failed: %s", exc)
            health_status["components"]["ollama"] = "unavailable (fallback active)"
            health_status["status"] = "degraded"
        except Exception as exc:
            logger.error("Ollama health check unexpected error: %s", exc)
            health_status["components"]["ollama"] = "unavailable (fallback active)"
            health_status["status"] = "degraded"

    try:
        if model_store.get_model("scibert_model") is not None:
            health_status["components"]["ai_models"] = "loaded"
        else:
            health_status["components"]["ai_models"] = "not_loaded"
    except Exception as exc:
        logger.error("AI models health check failed: %s", exc)
        health_status["components"]["ai_models"] = "error"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return health_status, status_code


async def _build_readiness_payload() -> tuple[dict, int]:
    from app.db.supabase_client import check_supabase_health
    from app.services.model_store import model_store

    checks: dict[str, Any] = {}
    is_ready = True
    dependency_status: dict[str, Any] = {}

    try:
        from app.cache.redis_cache import redis_cache
        redis_health = redis_cache.health()
        checks["redis"] = redis_health["status"]
    except Exception as exc:
        logger.debug("Redis health check skipped: %s", exc)
        checks["redis"] = "unavailable"

    try:
        sb_health = check_supabase_health()
        checks["database"] = sb_health.get("status", "unknown")
        if sb_health.get("status") == "healthy":
            pass
        elif sb_health.get("status") == "unconfigured":
            # Allow local/dev to run without Supabase configured.
            if not settings.DEBUG:
                is_ready = False
        else:
            is_ready = False
    except Exception as exc:
        checks["database"] = f"unhealthy: {str(exc)}"
        is_ready = False

    if settings.GROBID_ENABLED:
        grobid_status = await _probe_service_targets(
            service_name="grobid",
            urls=_service_urls("get_grobid_urls"),
            health_path=_service_health_path("grobid"),
            timeout_seconds=2.0,
        )
        dependency_status["grobid"] = grobid_status
        checks["grobid"] = grobid_status["status"]
        if grobid_status["status"] != "ready":
            is_ready = False
    else:
        dependency_status["grobid"] = {
            "status": "disabled",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "last_probe": {"endpoint": None, "http_status": None, "error": "disabled"},
        }
        checks["grobid"] = "disabled"

    dependency_status["docling"] = await _probe_service_targets(
        service_name="docling",
        urls=_service_urls("get_docling_urls"),
        health_path=_service_health_path("docling"),
        timeout_seconds=2.0,
    )
    checks["docling"] = dependency_status["docling"]["status"]

    dependency_status["ocr"] = await _probe_service_targets(
        service_name="ocr",
        urls=_service_urls("get_ocr_urls"),
        health_path=_service_health_path("ocr"),
        timeout_seconds=2.0,
    )
    checks["ocr"] = dependency_status["ocr"]["status"]

    dependency_status["docx_converter"] = await _probe_service_targets(
        service_name="docx_converter",
        urls=_service_urls("get_docx_converter_urls"),
        health_path=_service_health_path("docx_converter"),
        timeout_seconds=2.0,
    )
    checks["docx_converter"] = dependency_status["docx_converter"]["status"]

    nougat_urls = _service_urls("get_nougat_urls")
    if getattr(settings, "ENABLE_NOUGAT_PARSER", False):
        if nougat_urls:
            dependency_status["nougat"] = await _probe_service_targets(
                service_name="nougat",
                urls=nougat_urls,
                health_path=_service_health_path("nougat"),
                timeout_seconds=2.0,
            )
            checks["nougat"] = dependency_status["nougat"]["status"]
            if dependency_status["nougat"]["status"] != "ready":
                is_ready = False
        else:
            dependency_status["nougat"] = {
                "status": "local_or_unconfigured",
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "last_probe": {"endpoint": None, "http_status": None, "error": "no_remote_urls"},
            }
            checks["nougat"] = "local_or_unconfigured"
    else:
        dependency_status["nougat"] = {
            "status": "disabled",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "last_probe": {"endpoint": None, "http_status": None, "error": "disabled"},
        }
        checks["nougat"] = "disabled"

    try:
        from app.services.llm_service import check_health as llm_check_health

        checks["llm_status"] = await llm_check_health()
    except Exception as exc:
        logger.error("LLM health check failed in readiness: %s", exc)
        checks["llm_status"] = "unknown"

    scibert_urls = _service_urls("get_scibert_urls")
    if should_enable_scibert():
        if scibert_urls:
            dependency_status["scibert"] = await _probe_service_targets(
                service_name="scibert",
                urls=scibert_urls,
                health_path=_service_health_path("scibert"),
                timeout_seconds=2.0,
            )
            checks["scibert"] = dependency_status["scibert"]["status"]
            checks["ai_models"] = "remote"
            if dependency_status["scibert"]["status"] != "ready":
                is_ready = False
        else:
            try:
                if model_store.get_model("scibert_model") is not None:
                    checks["ai_models"] = "loaded"
                    checks["scibert"] = "local"
                else:
                    checks["ai_models"] = "not_loaded"
                    checks["scibert"] = "local_unavailable"
                    is_ready = False
            except Exception as exc:
                logger.error("Scibert local model check failed: %s", exc)
                checks["ai_models"] = "error"
                checks["scibert"] = "local_error"
                is_ready = False
    else:
        checks["ai_models"] = "disabled"
        checks["scibert_gate"] = get_scibert_gate_state()
        dependency_status["scibert"] = {
            "status": "disabled",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "last_probe": {"endpoint": None, "http_status": None, "error": "disabled"},
        }

    payload = {
        "ready": is_ready,
        "checks": checks,
        "dependencies": dependency_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return payload, 200 if is_ready else 503


async def get_readiness_payload(*, force_refresh: bool = False) -> tuple[dict, int]:
    global _readiness_cache_payload, _readiness_cache_status_code, _readiness_cache_expiry

    ttl_seconds = _readiness_ttl_seconds()
    now = monotonic()
    if (
        not force_refresh
        and ttl_seconds > 0
        and _readiness_cache_payload is not None
        and now < _readiness_cache_expiry
    ):
        return _clone_payload(_readiness_cache_payload), _readiness_cache_status_code

    async with _get_readiness_cache_lock():
        now = monotonic()
        if (
            not force_refresh
            and ttl_seconds > 0
            and _readiness_cache_payload is not None
            and now < _readiness_cache_expiry
        ):
            return _clone_payload(_readiness_cache_payload), _readiness_cache_status_code

        payload, status_code = await _build_readiness_payload()
        if ttl_seconds > 0:
            _readiness_cache_payload = payload
            _readiness_cache_status_code = status_code
            _readiness_cache_expiry = now + ttl_seconds
        else:
            invalidate_readiness_cache()

        return _clone_payload(payload), status_code


async def get_health_payload(*, force_refresh: bool = False) -> tuple[dict, int]:
    global _health_cache_payload, _health_cache_status_code, _health_cache_expiry

    ttl_seconds = _health_ttl_seconds()
    now = monotonic()
    if (
        not force_refresh
        and ttl_seconds > 0
        and _health_cache_payload is not None
        and now < _health_cache_expiry
    ):
        return _clone_payload(_health_cache_payload), _health_cache_status_code

    async with _get_health_cache_lock():
        now = monotonic()
        if (
            not force_refresh
            and ttl_seconds > 0
            and _health_cache_payload is not None
            and now < _health_cache_expiry
        ):
            return _clone_payload(_health_cache_payload), _health_cache_status_code

        payload, status_code = await _build_health_payload()
        if ttl_seconds > 0:
            _health_cache_payload = payload
            _health_cache_status_code = status_code
            _health_cache_expiry = now + ttl_seconds
        else:
            invalidate_health_cache()

        return _clone_payload(payload), status_code
