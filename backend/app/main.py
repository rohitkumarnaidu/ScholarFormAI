import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __description__, __title__, __version__
from app.api.routes import router as api_router
from app.api.update_routes import router as update_router
from app.api.issue_routes import router as issue_router
from app.core.config import settings
from app.core.errors import ErrorMiddleware
from app.core.exceptions import AMFError
from app.core.health import HealthChecker
from app.core.logging_config import setup_logging
from app.core.middleware import (
    AuditLogMiddleware,
    CorrelationIDMiddleware,
    RateLimitMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
    TimingMiddleware,
)
from app.core.sentry import SentryConfig, init_sentry
from app.core.versioning import VersioningMiddleware

setup_logging(settings.LOG_LEVEL, settings.ENVIRONMENT)
logger = logging.getLogger(__name__)

sentry_dsn = settings.SENTRY_DSN if hasattr(settings, "SENTRY_DSN") else None
if sentry_dsn:
    init_sentry(SentryConfig(dsn=sentry_dsn, environment=settings.ENVIRONMENT))

health_checker = HealthChecker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Automated Manuscript Formatter API v%s", __version__)
    app.state.start_time = time.time()
    app.state.health_checker = health_checker
    yield
    logger.info("Shutting down Automated Manuscript Formatter API")


app = FastAPI(
    title=__title__,
    description=__description__,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    contact={"name": "AMF Team", "email": "team@amf.dev"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID", "X-Request-Time"],
)

app.add_middleware(TimingMiddleware)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(RequestValidationMiddleware, max_content_length=settings.MAX_UPLOAD_SIZE)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(VersioningMiddleware)
app.add_middleware(RateLimitMiddleware, default_limit=60, window_seconds=60)
app.add_middleware(AuditLogMiddleware)

app.add_middleware(ErrorMiddleware)

app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(update_router, prefix=settings.API_PREFIX)
app.include_router(issue_router, prefix=settings.API_PREFIX)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    response = await call_next(request)
    elapsed = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Request-Time"] = f"{elapsed:.3f}s"
    logger.debug("Request %s %s completed in %.3fs", request.method, request.url.path, elapsed)
    return response


@app.exception_handler(AMFError)
async def amf_exception_handler(request: Request, exc: AMFError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message, "details": exc.details},
        headers={"X-Error-Code": exc.code},
    )


@app.get("/health")
async def health():
    return health_checker.liveness()


@app.get("/ready")
async def readiness():
    return health_checker.readiness()


@app.get("/health/detailed")
async def detailed_health():
    return health_checker.detailed()


@app.get("/metrics")
async def metrics():
    from app.core.telemetry import MetricsCollector

    collector = MetricsCollector()
    return JSONResponse(
        content=collector.get_metrics(), headers={"Content-Type": "text/plain; version=0.0.4"}
    )
