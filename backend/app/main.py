# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler as fastapi_http_exception_handler,
    request_validation_exception_handler as fastapi_validation_exception_handler,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.encoders import jsonable_encoder
from app.config.settings import settings
from app.exceptions import ScholarFormError
from app.middleware.request_id import RequestIdMiddleware, get_request_id
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.tier_rate_limit import TierRateLimitMiddleware
from app.services.health_checks import get_health_payload, get_readiness_payload
from app.schemas.api_envelope import error_response
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize logging — kept commented out so terminal output remains visible during development
# from app.config.logging_config import setup_logging
# setup_logging()

# Phase 2: Silence Global AI Startup Noise
import os
import asyncio
import logging
# Optional structured logging for production environments.
if settings.ENABLE_STRUCTURED_LOGGING:
    from app.config.logging_config import setup_logging
    setup_logging()

# DISABLED: Auto-delete feature temporarily removed per user request
# from app.utils.cleanup import cleanup_old_uploads
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
# Keep transformer/tokenizer noise low without importing heavy modules at startup.
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Basic logger for this module (terminal output preserved)
logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    SLOWAPI_AVAILABLE = True
except Exception:
    Limiter = None  # type: ignore[assignment]
    _rate_limit_exceeded_handler = None  # type: ignore[assignment]
    RateLimitExceeded = None  # type: ignore[assignment]
    SlowAPIMiddleware = None  # type: ignore[assignment]
    get_remote_address = None  # type: ignore[assignment]
    SLOWAPI_AVAILABLE = False

# --------------------------------------------------------


from app.pipeline.safety import safe_execution
from app.services.enhancement_manager import enhancement_manager

_queue_depth_redis_client = None


from app.routers.v1._helpers import DEFAULT_ERROR_CODES


def build_error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    payload = error_response(
        code=code,
        message=message,
        request_id=get_request_id(request),
        details=jsonable_encoder(details) if details is not None else None,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


def _build_cors_origins(raw_origins: str) -> list[str]:
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

    # In local development, Next/Vite frequently shift to the next available port
    # (3001, 3002, etc.). Keep loopback origins open on common dev ports so the
    # browser does not fail CORS preflight with a generic "Failed to fetch".
    if settings.DEBUG:
        loopback_hosts = ("localhost", "127.0.0.1")
        dev_ports = tuple(range(3000, 3011)) + (4173, 5173)
        for host in loopback_hosts:
            for port in dev_ports:
                candidate = f"http://{host}:{port}"
                if candidate not in origins:
                    origins.append(candidate)

    return origins


def _cleanup_expired_uploads(*, upload_dir: str = "uploads", retention_days: int) -> int:
    if not os.path.isdir(upload_dir):
        return 0

    cutoff_epoch = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    deleted = 0
    for entry in os.scandir(upload_dir):
        if not entry.is_file():
            continue
        try:
            if entry.stat().st_mtime < cutoff_epoch:
                os.remove(entry.path)
                deleted += 1
        except OSError as exc:
            logger.warning("Cleanup failed for %s: %s", entry.path, exc)
    return deleted


async def _periodic_file_cleanup(retention_days: int) -> None:
    while True:
        cleaned = _cleanup_expired_uploads(retention_days=retention_days)
        logger.info(
            "Scheduled file cleanup complete. Removed %d files older than %d days.",
            cleaned,
            retention_days,
        )
        await asyncio.sleep(24 * 60 * 60)


def _fetch_queue_depths() -> dict[str, int]:
    if not settings.REDIS_ENABLED:
        return {"interactive": 0, "batch": 0}
    try:
        global _queue_depth_redis_client
        if _queue_depth_redis_client is None:
            import redis
            _queue_depth_redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return {
            queue: int(_queue_depth_redis_client.llen(queue) or 0)
            for queue in ("interactive", "batch")
        }
    except Exception as exc:
        logger.debug("Queue depth fetch failed: %s", exc)
        _queue_depth_redis_client = None
        return {"interactive": 0, "batch": 0}


async def _periodic_queue_depth_update(interval_seconds: int = 30) -> None:
    while True:
        depths = await asyncio.to_thread(_fetch_queue_depths)
        try:
            from app.middleware.prometheus_metrics import MetricsManager
            for queue, depth in depths.items():
                MetricsManager.set_celery_queue_depth(queue, depth)
        except Exception:
            pass
        await asyncio.sleep(interval_seconds)


def _is_v1_request(request: Request) -> bool:
    return request.url.path.startswith("/api/v1/")


async def _probe_grobid_startup(*, attempts: int = 3, timeout_seconds: float = 2.0) -> bool:
    if not settings.GROBID_ENABLED:
        logger.info("Startup: GROBID probe skipped (GROBID_ENABLED=false).")
        return False

    import httpx

    candidate_urls = list(getattr(settings, "get_grobid_urls", lambda: [settings.GROBID_URL])())
    if not candidate_urls:
        candidate_urls = [settings.GROBID_URL]
    health_path = str(getattr(settings, "get_service_health_path", lambda _name: "/api/isalive")("grobid"))
    if not health_path.startswith("/"):
        health_path = f"/{health_path}"
    if len(health_path) > 1:
        health_path = health_path.rstrip("/")

    last_error = "unknown"
    for endpoint in candidate_urls:
        probe_url = f"{endpoint.rstrip('/')}{health_path}"
        for attempt in range(1, max(1, attempts) + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                    response = await client.get(probe_url)
                if response.status_code == 200:
                    logger.info("Startup: GROBID probe succeeded on attempt %d via %s.", attempt, endpoint)
                    return True
                last_error = f"HTTP {response.status_code} from {endpoint}"
            except Exception as exc:
                last_error = f"{endpoint}: {exc}"

            if attempt < attempts:
                await asyncio.sleep(min(float(attempt), 3.0))

    logger.warning(
        "Startup: GROBID probe failed after %d attempts (%s). "
        "The app will continue in degraded mode and rely on downstream fallbacks.",
        attempts * max(1, len(candidate_urls)),
        last_error,
    )
    return False


# ── Lifespan (replaces deprecated @app.on_event) ─────────────────────────────
def _reset_interrupted_jobs_on_startup() -> None:
    """Best-effort reset for jobs interrupted by a previous restart."""
    try:
        from app.db.supabase_client import get_supabase_client

        sb = get_supabase_client()
        if sb is not None:
            result = sb.table("documents").select("id").eq("status", "PROCESSING").execute()
            interrupted = result.data or []
            if interrupted:
                ids = [row["id"] for row in interrupted]
                logger.info("Startup: Found %d interrupted jobs. Marking as FAILED.", len(ids))
                sb.table("documents").update(
                    {
                        "status": "FAILED",
                        "error_message": "Processing interrupted by server restart.",
                    }
                ).in_("id", ids).execute()
        else:
            logger.warning("Startup DB Link Status: UNCONFIGURED. App starting in degraded mode.")
    except Exception as exc:
        logger.warning("Startup DB Link Status: UNREACHABLE. Error: %s", exc)
        logger.info(
            "Note: App is starting in degraded mode. DB-dependent endpoints will fail at request-time."
        )


def _refresh_enhancement_capabilities() -> None:
    profile = enhancement_manager.refresh()
    logger.info("Enhancement capabilities loaded: %s", profile.to_dict())


def _preload_preview_css() -> None:
    from app.services.preview_renderer import preload_template_css

    preload_template_css()
    logger.info("Preview template CSS preloaded.")


def _load_optional_routers(target_app: FastAPI) -> None:
    """Load heavy API routers lazily so module import can stay fast on low-memory hosts."""
    if getattr(target_app.state, "_routers_loaded", False):
        return

    from app.routers.v1 import v1_router
    from app.routers import preview

    target_app.include_router(v1_router)
    target_app.include_router(preview.router)
    target_app.state._routers_loaded = True
    logger.info("Startup: API routers loaded.")


def _validate_startup() -> None:
    """Comprehensive startup validation of required and optional dependencies."""
    required_keys = {
        "ALGORITHM": getattr(settings, "ALGORITHM", None),
    }
    missing_required = [name for name, value in required_keys.items() if not value]
    if missing_required:
        logger.error("Startup validation FAILED: missing required settings: %s", missing_required)
        raise RuntimeError(f"Missing required settings: {', '.join(missing_required)}")

    optional_api_keys = {
        "NVIDIA_API_KEY": getattr(settings, "NVIDIA_API_KEY", None),
        "GROQ_API_KEY": getattr(settings, "GROQ_API_KEY", None),
        "OPENAI_API_KEY": getattr(settings, "OPENAI_API_KEY", None),
        "OPENROUTER_API_KEY": getattr(settings, "OPENROUTER_API_KEY", None),
        "ANTHROPIC_API_KEY": getattr(settings, "ANTHROPIC_API_KEY", None),
    }
    missing_optional = [name for name, value in optional_api_keys.items() if not value]
    if missing_optional:
        logger.warning(
            "Startup validation: optional API keys not configured: %s. "
            "LLM fallback tiers will be limited.",
            ", ".join(missing_optional),
        )

    db_url = getattr(settings, "SUPABASE_DB_URL", None)
    if not db_url:
        logger.warning(
            "Startup validation: SUPABASE_DB_URL not set. "
            "Alembic migrations will not work until configured."
        )

    if getattr(settings, "REDIS_ENABLED", False):
        redis_url = getattr(settings, "REDIS_URL", None)
        if not redis_url:
            logger.error(
                "Startup validation: REDIS_ENABLED=true but REDIS_URL is not set."
            )
        else:
            try:
                import redis
                client = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
                client.ping()
                logger.info("Startup validation: Redis connection OK at %s", redis_url)
            except Exception as e:
                logger.warning(
                    "Startup validation: Redis connection failed (%s). "
                    "Caching will be disabled until Redis is available.",
                    e,
                )

    supabase_url = getattr(settings, "SUPABASE_URL", None)
    supabase_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
    if supabase_url and supabase_key:
        try:
            from app.db.supabase_client import check_supabase_health
            health = check_supabase_health()
            if health.get("status") == "healthy":
                logger.info("Startup validation: Supabase database connection OK.")
            else:
                logger.warning(
                    "Startup validation: Supabase database health check returned: %s",
                    health.get("status"),
                )
        except Exception as e:
            logger.warning(
                "Startup validation: Supabase database connection failed: %s. "
                "App will start in degraded mode.",
                e,
            )
    else:
        logger.warning(
            "Startup validation: Supabase credentials not fully configured. "
            "DB-dependent endpoints will return 503."
        )

    logger.info("Startup validation complete.")


_router_load_lock: asyncio.Lock | None = None


async def _ensure_routers_loaded(target_app: FastAPI) -> None:
    """
    Lazily load heavy API routers on first API request so cold boot can bind a port fast.
    """
    if getattr(target_app.state, "_routers_loaded", False):
        return

    global _router_load_lock
    if _router_load_lock is None:
        _router_load_lock = asyncio.Lock()

    async with _router_load_lock:
        if getattr(target_app.state, "_routers_loaded", False):
            return
        await _run_startup_step(
            "router_load",
            lambda: _load_optional_routers(target_app),
            timeout_seconds=20.0,
        )


async def _run_startup_step(
    step_name: str,
    callback,
    *,
    timeout_seconds: float,
    default_value=None,
):
    """
    Run a startup callback with a hard timeout so service boot cannot hang.
    """
    try:
        return await asyncio.wait_for(asyncio.to_thread(callback), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(
            "Startup step '%s' timed out after %.1fs. Continuing in degraded mode.",
            step_name,
            timeout_seconds,
        )
    except Exception as exc:
        logger.warning(
            "Startup step '%s' failed: %s. Continuing in degraded mode.",
            step_name,
            exc,
        )
    return default_value


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: startup and shutdown logic.
    Note: This project intentionally avoids automated pipeline testing at this stage.
    """
    # ── STARTUP ──
    # DISABLED: Auto-delete feature temporarily removed per user request
    # cleanup_task = asyncio.create_task(cleanup_old_uploads())
    cleanup_task = None
    queue_metrics_task = None

    # ── STARTUP VALIDATION ──
    await _run_startup_step(
        "startup_validation",
        _validate_startup,
        timeout_seconds=15.0,
    )

    enable_cleanup = settings.ENABLE_FILE_CLEANUP
    retention_days = int(settings.RETENTION_DAYS)
    if enable_cleanup:
        cleaned = _cleanup_expired_uploads(retention_days=retention_days)
        logger.info(
            "Startup file cleanup complete. Removed %d files older than %d days.",
            cleaned,
            retention_days,
        )
        cleanup_task = asyncio.create_task(_periodic_file_cleanup(retention_days))
    else:
        logger.info("File cleanup disabled (ENABLE_FILE_CLEANUP=false in .env).")

    queue_metrics_task = asyncio.create_task(_periodic_queue_depth_update())

    with safe_execution("Application Startup"):
        await _run_startup_step(
            "supabase_reset_interrupted_jobs",
            _reset_interrupted_jobs_on_startup,
            timeout_seconds=8.0,
        )

        try:
            app.state.grobid_startup_probe_ok = await asyncio.wait_for(
                _probe_grobid_startup(),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            app.state.grobid_startup_probe_ok = False
            logger.warning(
                "Startup step 'grobid_probe' timed out after 25.0s. Continuing in degraded mode."
            )

        if settings.PRELOAD_AI_MODELS and not settings.LOW_MEMORY_MODE:
            # Phase 2: AI Model Pre-loading (optional, can be disabled for low-memory deploys)
            from app.services.model_store import model_store

            logger.info("Startup: Pre-loading AI models into memory...")
            try:
                from app.pipeline.intelligence.rag_engine import get_rag_engine

                rag = get_rag_engine()
                model_store.set_model("rag_engine", rag)
                model_store.set_model("embedding_model", rag.embedding_model)
                logger.info("RAG Engine initialized.")

                logger.info("Startup: AI models loaded and registered successfully.")
            except Exception as e:
                logger.warning("AI Model Pre-load Warning: %s. Falling back to lazy-loading.", e)
        else:
            logger.info(
                "Startup: Skipping AI model pre-load "
                "(PRELOAD_AI_MODELS=%s, LOW_MEMORY_MODE=%s).",
                settings.PRELOAD_AI_MODELS,
                settings.LOW_MEMORY_MODE,
            )
        await _run_startup_step(
            "enhancement_refresh",
            _refresh_enhancement_capabilities,
            timeout_seconds=8.0,
        )
        await _run_startup_step(
            "preview_css_preload",
            _preload_preview_css,
            timeout_seconds=5.0,
        )
    yield  # App is running

    # ── SHUTDOWN ──
    if queue_metrics_task is not None:
        queue_metrics_task.cancel()
        try:
            await queue_metrics_task
        except asyncio.CancelledError:
            pass
    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("ScholarForm AI shutting down...")


# ── App creation ──────────────────────────────────────────────────────────────
# Disable Swagger/ReDoc in production to avoid exposing API internals
_is_debug = getattr(settings, "DEBUG", False)
# FastAPI compatibility: 0.128.0 removed support for APIRouter webhooks `on_startup`
# keyword. Pinned to 0.127.1 (Starlette 0.50.0) until the v1 router chain is migrated
# to the newer lifespan pattern. See AGENTS.md requirements for upgrade path.
app = FastAPI(
    title="ScholarForm AI Backend",
    description="Backend API for ScholarForm AI with Supabase Auth",
    version="1.0.0",
    docs_url="/docs" if _is_debug else None,
    redoc_url="/redoc" if _is_debug else None,
    openapi_url="/openapi.json" if _is_debug else None,
    lifespan=lifespan,
)

if SLOWAPI_AVAILABLE and Limiter is not None and get_remote_address is not None:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{int(getattr(settings, 'GLOBAL_RATE_LIMIT_PER_MINUTE', 120))}/minute"],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info("SlowAPI global rate limiting enabled.")
else:
    logger.warning("SlowAPI not available; falling back to custom middleware-only rate limiting.")


@app.exception_handler(ScholarFormError)
async def scholarform_exception_handler(request: Request, exc: ScholarFormError):
    return build_error_response(
        request,
        status_code=exc.http_status,
        code=DEFAULT_ERROR_CODES.get(exc.http_status, "API_ERROR"),
        message=str(exc),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if not _is_v1_request(request):
        return await fastapi_http_exception_handler(request, exc)

    detail = exc.detail
    if isinstance(detail, str):
        message = detail
        details = None
    else:
        message = "Request failed"
        details = {"detail": detail}

    code = DEFAULT_ERROR_CODES.get(exc.status_code, "API_ERROR")
    response = build_error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
        details=details,
    )
    for header, value in (exc.headers or {}).items():
        response.headers[header] = value
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError):
    if not _is_v1_request(request):
        return await fastapi_validation_exception_handler(request, exc)

    return build_error_response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details={"detail": exc.errors()},
    )

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# CORS Configuration (from environment + local dev fallbacks)
origins = _build_cors_origins(settings.CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Requested-With",
        "Accept",
        "X-Request-Id",
        "X-CSRF-Token",
        "Idempotency-Key",
    ],
)

# Request ID Middleware MUST be first after CORS so every request gets an ID.
app.add_middleware(RequestIdMiddleware)

# Rate Limiting Middleware (DoS Protection)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=int(getattr(settings, "GLOBAL_RATE_LIMIT_PER_MINUTE", 120)),
)
app.add_middleware(TierRateLimitMiddleware, guest_daily_limit=5)

# Security Headers Middleware (CSP, X-Frame-Options, etc.)
from app.middleware.security_headers import SecurityHeadersMiddleware, MaxBodySizeMiddleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(MaxBodySizeMiddleware, max_size=60 * 1024 * 1024)  # 60MB global limit

# CSRF Protection Middleware
from app.middleware.csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware)

# Feature Flag Middleware (dev only — adds X-Feature-Flags header)
from app.middleware.feature_flags import FeatureFlagMiddleware
app.add_middleware(FeatureFlagMiddleware)

# Monitoring Middleware (adds request timing and structured logging)
from app.middleware.monitoring import MonitoringMiddleware
app.add_middleware(MonitoringMiddleware)

_HTTPS_REDIRECT_EXEMPT_PATHS = {
    "/health",
    "/ready",
    "/api/v1/health",
    "/api/v1/health/live",
    "/api/v1/health/ready",
    "/api/v1/health/admin",
}


def _normalize_request_path(path: str | None) -> str:
    if not path:
        return "/"
    normalized = path if path.startswith("/") else f"/{path}"
    if len(normalized) > 1:
        normalized = normalized.rstrip("/")
    return normalized or "/"


def _should_bypass_https_redirect(path: str | None) -> bool:
    return _normalize_request_path(path) in _HTTPS_REDIRECT_EXEMPT_PATHS


# HTTPS Redirect + HSTS (production only)
if settings.FORCE_HTTPS and not settings.DEBUG:
    from app.middleware.https_redirect import HSTSMiddleware

    @app.middleware("http")
    async def enforce_https_except_health(request: Request, call_next):
        request_path = request.url.path
        if request.url.scheme != "https" and not _should_bypass_https_redirect(request_path):
            redirect_url = str(request.url.replace(scheme="https"))
            return RedirectResponse(url=redirect_url, status_code=307)

        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
else:
    # Development: still add security headers but skip HSTS
    @app.middleware("http")
    async def add_security_headers_dev(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


@app.middleware("http")
async def lazy_router_loader(request: Request, call_next):
    path = request.url.path or ""
    if (
        (path.startswith("/api/v1/") or path.startswith("/api/preview"))
        and not getattr(app.state, "_routers_loaded", False)
    ):
        await _ensure_routers_loaded(app)
    return await call_next(request)


@app.middleware("http")
async def audit_write_operations(request: Request, call_next):
    response = await call_next(request)
    try:
        from app.services.audit_log_service import audit_log_service
        await audit_log_service.log_http_write(
            request,
            status_code=response.status_code,
        )
    except Exception as exc:
        logger.debug("Audit middleware skipped due to logging error: %s", exc)
    return response

# Document Generator (generate from scratch — no upload needed)
# Hard-cut migration: only /api/v1 routers are mounted from app.main.


@app.get("/ready")
async def readiness_probe():
    """
    Readiness probe for operational environments (K8s, Docker).
    Checks availability of critical dependencies and AI models.
    """
    payload, status_code = await get_readiness_payload()
    return JSONResponse(content=payload, status_code=status_code)

@app.get("/")
async def root():
    return {"message": "ScholarForm AI Backend is running"}

@app.get("/health")
async def health_check():
    """
    Liveness endpoint for platform health checks.
    Always returns HTTP 200 so host-level liveness does not flap when
    optional dependencies are degraded; use /ready or /api/v1/health/ready
    for strict readiness.
    """
    payload, _status_code = await get_health_payload()
    return JSONResponse(content=payload, status_code=200)


