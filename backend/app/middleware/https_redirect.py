# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
HTTPS Redirect Middleware — forces all HTTP requests to HTTPS.
Adds HSTS header for browsers to remember HTTPS-only policy.
"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirects all HTTP requests to HTTPS.

    Skips redirect for:
    - Health check endpoints (used by load balancers)
    - Localhost requests (development)
    - Requests already on HTTPS
    """

    HEALTH_PATHS = {"/api/v1/health", "/api/v1/health/live", "/health", "/ready", "/readyz"}

    async def dispatch(self, request: Request, call_next):
        if request.url.scheme == "https":
            return await call_next(request)

        if request.url.hostname in ("localhost", "127.0.0.1", "0.0.0.0"):  # nosec
            return await call_next(request)

        if request.url.path in self.HEALTH_PATHS:
            return await call_next(request)

        https_url = request.url.replace(scheme="https")
        logger.info("Redirecting HTTP → HTTPS: %s", request.url.path)
        return RedirectResponse(url=str(https_url), status_code=307)


class HSTSMiddleware(BaseHTTPMiddleware):
    """
    Adds Strict-Transport-Security header to all HTTPS responses.

    HSTS tells browsers to always use HTTPS for this domain,
    preventing SSL stripping attacks.
    """

    def __init__(self, app, max_age: int = 31536000, include_subdomains: bool = True, preload: bool = True):
        super().__init__(app)
        self.max_age = max_age
        self.include_subdomains = include_subdomains
        self.preload = preload

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.url.scheme == "https":
            hsts_value = f"max-age={self.max_age}"
            if self.include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.preload:
                hsts_value += "; preload"

            response.headers["Strict-Transport-Security"] = hsts_value
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
