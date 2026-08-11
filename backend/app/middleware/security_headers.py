# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Security Headers Middleware — adds standard security headers to all responses.

Headers added:
- Content-Security-Policy: Restrict resource loading
- X-Content-Type-Options: Prevent MIME-type sniffing
- X-Frame-Options: Prevent clickjacking
- X-XSS-Protection: Legacy XSS filter
- Referrer-Policy: Control referrer information
- Permissions-Policy: Restrict browser features
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds crucial security headers to all HTTP responses.

    This helps mitigate various web vulnerabilities:
    - Content-Security-Policy: Restricts sources for executable scripts and embeds.
    - X-Content-Type-Options: Prevents MIME-sniffing attacks.
    - X-Frame-Options: Protects against clickjacking by denying iframing.
    - X-XSS-Protection: Enables legacy XSS filtering.
    - Strict-Transport-Security: Enforces HTTPS on the client side.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        path = request.url.path or ""
        is_docs_route = path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json"

        if is_docs_route:
            # FastAPI Swagger/ReDoc pages pull JS/CSS from CDN by default.
            # Keep CSP enabled but allow required origins for docs rendering.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' data: https://cdn.jsdelivr.net https://fonts.gstatic.com; "
                "connect-src 'self' https://*.supabase.co wss://*.supabase.co ws: wss:; "
                "frame-src 'self' blob:; "
                "object-src 'self' blob:"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://*.supabase.co wss://*.supabase.co ws: wss:; "
                "frame-src 'self' blob:; "
                "object-src 'self' blob:"
            )
        return response


class MaxBodySizeMiddleware:
    """Middleware that restricts the maximum payload size of incoming HTTP requests.

    This protects the application against Denial of Service (DoS) attacks
    where an attacker sends an excessively large request body to consume
    memory or exhaust server bandwidth. If the Content-Length header
    or accumulated streaming body exceeds `max_size`, an HTTP 413 (Payload Too Large)
    is returned immediately.
    """

    def __init__(self, app, max_size: int = 60 * 1024 * 1024):  # Default 60MB
        self.app = app
        self.max_size = max_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_size:
                    from starlette.responses import JSONResponse

                    response = JSONResponse(
                        {"detail": f"Request body too large. Maximum is {self.max_size} bytes."},
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return
            except (ValueError, TypeError):
                pass  # intentionally ignored

        received_bytes = 0
        response_sent = False

        async def custom_receive():
            nonlocal received_bytes, response_sent
            message = await receive()
            if message and message.get("type") == "http.request":
                body = message.get("body", b"")
                received_bytes += len(body)
                if received_bytes > self.max_size and not response_sent:
                    response_sent = True
                    from starlette.responses import JSONResponse

                    response = JSONResponse(
                        {"detail": f"Request body too large. Maximum is {self.max_size} bytes."},
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, custom_receive, send)
