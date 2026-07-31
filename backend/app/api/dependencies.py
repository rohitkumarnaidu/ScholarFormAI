import logging
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, status

from app.core.cache import CacheBackend, get_cache_backend
from app.core.config import settings
from app.services.formatter import ManuscriptFormatter
from app.services.validator import ManuscriptValidator

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> dict[str, Any] | None:
    api_key = request.headers.get("X-API-Key", "")
    authorization = request.headers.get("Authorization", "")

    if api_key and settings.SECRET_KEY:
        if api_key != settings.SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "UNAUTHORIZED", "message": "Invalid API key"},
            )
        return {"id": "api_user", "type": "api_key", "roles": ["user"]}

    if authorization.startswith("Bearer "):
        token = authorization[7:]
        if settings.SECRET_KEY and token == settings.SECRET_KEY:
            return {"id": "bearer_user", "type": "bearer_token", "roles": ["user"]}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Invalid bearer token"},
        )

    return None


async def optional_current_user(request: Request) -> dict[str, Any] | None:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def get_db(request: Request) -> Any:
    if not settings.DATABASE_URL:
        logger.debug("No database configured, returning None")
        yield None
        return
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
        session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = session_local()
        try:
            yield db
        finally:
            db.close()
    except ImportError:
        logger.warning("SQLAlchemy not installed, database unavailable")
        yield None
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        yield None


async def get_cache(request: Request) -> CacheBackend:
    return get_cache_backend()


async def get_validator(request: Request) -> ManuscriptValidator:
    return ManuscriptValidator()


async def get_formatter(request: Request) -> ManuscriptFormatter:
    return ManuscriptFormatter()


def require_rate_limit(path_limits: list[tuple[str, int]]) -> Callable:
    """Configure per-endpoint rate limits for dependency injection.

    Usage:
        @router.post("/format", dependencies=[Depends(require_rate_limit(
            [("/api/v1/format", 10)]
        ))])
    """

    async def rate_limit_dependency(request: Request) -> None:
        path = request.url.path
        for prefix, limit in path_limits:
            if path.startswith(prefix):
                request.state.rate_limit_path = prefix
                request.state.rate_limit_value = limit
                return
        request.state.rate_limit_path = None
        request.state.rate_limit_value = None

    return rate_limit_dependency


async def request_id(request: Request) -> str:
    rid = request.headers.get("X-Request-ID", request.headers.get("X-Correlation-ID"))
    if not rid:
        rid = str(uuid.uuid4())
    request.state.request_id = rid
    return rid


async def correlation_id(request: Request) -> str:
    cid = request.headers.get("X-Correlation-ID", request.headers.get("X-Request-ID"))
    if not cid:
        cid = str(uuid.uuid4())
    request.state.correlation_id = cid
    return cid


async def validate_content_type(request: Request) -> None:
    if request.method in ("POST", "PUT", "PATCH"):
        content_type = request.headers.get("content-type", "").lower()
        if not content_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error": "MISSING_CONTENT_TYPE",
                    "message": "Content-Type header is required",
                },
            )
        if "application/json" not in content_type and "multipart/form-data" not in content_type:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error": "UNSUPPORTED_CONTENT_TYPE",
                    "message": f"Unsupported Content-Type: {content_type}",
                },
            )


async def get_api_version(request: Request) -> str:
    return getattr(request.state, "api_version", "1.0")


async def health_dependency(request: Request) -> dict[str, Any]:
    return {"status": "ok"}
