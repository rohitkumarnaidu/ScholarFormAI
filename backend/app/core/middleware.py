import logging
import re
import time
from collections import defaultdict
from collections.abc import Callable
from re import Pattern
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter per client IP with per-endpoint configuration."""

    def __init__(
        self,
        app: Any,
        default_limit: int = 60,
        window_seconds: int = 60,
        burst_multiplier: float = 1.5,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.window = window_seconds
        self.burst_multiplier = burst_multiplier
        self._buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"tokens": default_limit, "last_refill": time.time()}
        )
        self._path_limits: list[tuple[Pattern, int]] = [
            (re.compile(r"^/api/v1/format"), 10),
            (re.compile(r"^/api/v1/validate"), 30),
            (re.compile(r"^/api/v1/preview"), 20),
            (re.compile(r"^/api/v1/styles"), 100),
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/metrics", "/ready", "/live"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        limit = self.default_limit
        for pattern, path_limit in self._path_limits:
            if pattern.match(path):
                limit = path_limit
                break

        refill_rate = limit / self.window
        burst_capacity = int(limit * self.burst_multiplier)

        bucket = self._buckets[client_ip]
        now = time.time()
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(burst_capacity, bucket["tokens"] + elapsed * refill_rate)
        bucket["last_refill"] = now

        if bucket["tokens"] < 1:
            logger.warning("Rate limit exceeded for IP %s on %s", client_ip, path)
            return Response(
                content='{"error":"RATE_LIMIT_EXCEEDED","message":"Rate limit exceeded. '
                'Try again later.","retry_after":'
                + str(int(self.window))
                + "}",
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(int(self.window)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + self.window)),
                },
            )

        bucket["tokens"] -= 1
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Reset"] = str(int(bucket["last_refill"] + self.window))
        return response


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log all requests with structured JSON metadata."""

    def __init__(self, app: Any, exclude_paths: list[str] | None = None):
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or ["/health", "/metrics", "/ready", "/live"])
        self.audit_logger = logging.getLogger("audit")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        correlation_id = request.headers.get(
            "X-Correlation-ID", request.headers.get("X-Request-ID", "")
        )
        content_length = request.headers.get("content-length", "0")

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000
        status_code = response.status_code

        audit_record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "query_string": str(request.url.query),
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "user_agent": user_agent[:256],
            "content_length": content_length,
            "correlation_id": correlation_id,
            "response_size": response.headers.get("content-length", "0"),
        }

        log_fn = self.audit_logger.warning if status_code >= 400 else self.audit_logger.info
        log_fn("AuditLog %(method)s %(path)s %(status_code)d %(duration_ms)sms", audit_record)

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    def __init__(self, app: Any, csp_directives: dict[str, list[str]] | None = None):
        super().__init__(app)
        self.csp_directives = csp_directives or {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:"],
            "font-src": ["'self'"],
            "connect-src": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "object-src": ["'none'"],
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        csp_value = "; ".join(
            f"{key} {' '.join(values)}" for key, values in self.csp_directives.items()
        )
        response.headers["Content-Security-Policy"] = csp_value
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), interest-cohort=()"
        )
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a correlation ID propagated through headers."""

    def __init__(self, app: Any, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import uuid

        correlation_id = request.headers.get(self.header_name, request.headers.get("X-Request-ID"))
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Track and expose request timing metrics."""

    def __init__(self, app: Any):
        super().__init__(app)
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._max_samples = 10000

    @property
    def metrics(self) -> dict[str, dict[str, float]]:
        result = {}
        for path, durations in self._timings.items():
            if durations:
                result[path] = {
                    "count": len(durations),
                    "avg_ms": sum(durations) / len(durations),
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                    "p50_ms": sorted(durations)[len(durations) // 2],
                    "p95_ms": sorted(durations)[int(len(durations) * 0.95)],
                    "p99_ms": sorted(durations)[int(len(durations) * 0.99)],
                    "total_ms": sum(durations),
                }
        return result

    def get_prometheus_metrics(self) -> str:
        lines = []
        for path, durations in self._timings.items():
            if durations:
                path.replace("/", "_").replace("-", "_").strip("_")
                for duration in durations[-100:]:
                    lines.append(f'http_request_duration_ms{{path="{path}"}} {duration}')
                lines.append(f'http_request_count{{path="{path}"}} {len(durations)}')
        return "\n".join(lines)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/health", "/metrics", "/ready", "/live"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        path_key = f"{request.method} {request.url.path}"
        samples = self._timings[path_key]
        samples.append(elapsed_ms)
        if len(samples) > self._max_samples:
            self._timings[path_key] = samples[-self._max_samples // 2 :]

        response.headers["X-Request-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Validate Content-Type, max body size, and sanitize request paths."""

    def __init__(
        self,
        app: Any,
        max_content_length: int = 10 * 1024 * 1024,
        allowed_content_types: list[str] | None = None,
    ):
        super().__init__(app)
        self.max_body_size = max_content_length
        self.allowed_content_types = allowed_content_types or [
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
        ]
        self._path_traversal_pattern = re.compile(r"(\.\./|\.\\)")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        query = str(request.url.query)

        if self._path_traversal_pattern.search(path) or self._path_traversal_pattern.search(query):
            logger.warning("Path traversal attempt blocked: %s", path)
            return Response(
                content='{"error":"INVALID_PATH","message":"Invalid request path"}',
                status_code=400,
                media_type="application/json",
            )

        if request.method in ("POST", "PUT", "PATCH"):
            if request.url.path not in ("/health", "/metrics", "/ready", "/live"):
                request.headers.get("content-type", "").split(";")[0].strip().lower()
                content_length_str = request.headers.get("content-length", "0")

                if content_length_str.isdigit():
                    content_length = int(content_length_str)
                    if content_length > self.max_body_size:
                        logger.warning(
                            "Request too large: %d bytes from %s",
                            content_length,
                            request.client.host if request.client else "unknown",
                        )
                        return Response(
                            content=f'{{"error":"PAYLOAD_TOO_LARGE",'
                            f'"message":"Request body exceeds {self.max_body_size} bytes"}}',
                            status_code=413,
                            media_type="application/json",
                        )

        response = await call_next(request)
        return response
