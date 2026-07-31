import logging
import traceback
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)

ERROR_CATALOG: dict[str, dict[str, Any]] = {
    "UNKNOWN_ERROR": {
        "status_code": 500,
        "message": "An unexpected error occurred",
        "severity": "error",
    },
    "VALIDATION_ERROR": {
        "status_code": 400,
        "message": "Request validation failed",
        "severity": "error",
    },
    "STYLE_NOT_FOUND": {
        "status_code": 404,
        "message": "The requested formatting style was not found",
        "severity": "error",
    },
    "FORMATTING_ERROR": {
        "status_code": 422,
        "message": "Failed to format the manuscript",
        "severity": "error",
    },
    "RATE_LIMIT_EXCEEDED": {
        "status_code": 429,
        "message": "Rate limit exceeded. Please try again later.",
        "severity": "error",
    },
    "MANUSCRIPT_TOO_LARGE": {
        "status_code": 413,
        "message": "The manuscript exceeds the maximum allowed size",
        "severity": "error",
    },
    "UNSUPPORTED_FORMAT": {
        "status_code": 400,
        "message": "The input format is not supported",
        "severity": "error",
    },
    "MISSING_TITLE": {
        "status_code": 400,
        "message": "Manuscript title is required",
        "severity": "error",
    },
    "MISSING_AUTHORS": {
        "status_code": 400,
        "message": "At least one author is required",
        "severity": "error",
    },
    "MISSING_ABSTRACT": {
        "status_code": 400,
        "message": "Abstract is required for the selected style",
        "severity": "error",
    },
    "INVALID_PATH": {
        "status_code": 400,
        "message": "The request path contains invalid characters",
        "severity": "error",
    },
    "PAYLOAD_TOO_LARGE": {
        "status_code": 413,
        "message": "The request payload exceeds the maximum allowed size",
        "severity": "error",
    },
    "UPGRADE_REQUIRED": {
        "status_code": 426,
        "message": "A newer API version is required",
        "severity": "error",
    },
    "UNAUTHORIZED": {
        "status_code": 401,
        "message": "Authentication is required to access this resource",
        "severity": "error",
    },
    "FORBIDDEN": {
        "status_code": 403,
        "message": "You do not have permission to access this resource",
        "severity": "error",
    },
    "NOT_FOUND": {
        "status_code": 404,
        "message": "The requested resource was not found",
        "severity": "error",
    },
    "UNSUPPORTED_CONTENT_TYPE": {
        "status_code": 415,
        "message": "The request Content-Type is not supported",
        "severity": "error",
    },
    "INTERNAL_ERROR": {
        "status_code": 500,
        "message": "An internal server error occurred",
        "severity": "error",
    },
    "SERVICE_UNAVAILABLE": {
        "status_code": 503,
        "message": "The service is temporarily unavailable",
        "severity": "error",
    },
    "TITLE_TOO_LONG": {
        "status_code": 400,
        "message": "The manuscript title exceeds the maximum allowed length",
        "severity": "error",
    },
    "TOO_MANY_AUTHORS": {
        "status_code": 400,
        "message": "The manuscript has too many authors",
        "severity": "error",
    },
    "TOO_MANY_SECTIONS": {
        "status_code": 400,
        "message": "The manuscript has too many sections",
        "severity": "error",
    },
    "SECTION_DEPTH_EXCEEDED": {
        "status_code": 400,
        "message": "Section nesting depth exceeds the maximum allowed",
        "severity": "error",
    },
}


def get_error_info(error_code: str) -> dict[str, Any]:
    return ERROR_CATALOG.get(error_code, ERROR_CATALOG["UNKNOWN_ERROR"])


def format_error_response(
    error_code: str,
    message: str | None = None,
    details: Any | None = None,
    status_code: int | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    info = get_error_info(error_code)
    body: dict[str, Any] = {
        "error": error_code,
        "message": message or info["message"],
        "status_code": status_code or info["status_code"],
    }
    if details:
        body["details"] = details
    if request_id:
        body["request_id"] = request_id

    return JSONResponse(
        status_code=status_code or info["status_code"],
        content=body,
        headers={"X-Error-Code": error_code},
    )


def http_exception_to_error(request: Request, exc: HTTPException) -> JSONResponse:
    error_code = getattr(exc, "code", None)
    if not error_code:
        status_code_map: dict[int, str] = {
            400: "VALIDATION_ERROR",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "VALIDATION_ERROR",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_CONTENT_TYPE",
            422: "VALIDATION_ERROR",
            426: "UPGRADE_REQUIRED",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        error_code = status_code_map.get(exc.status_code, "UNKNOWN_ERROR")

    detail = exc.detail
    details = None
    if isinstance(detail, dict):
        details = detail.get("details")
        error_code = detail.get("error", error_code)
        message = detail.get("message", str(detail))
    elif isinstance(detail, list):
        details = detail
        message = "Validation failed"
    else:
        message = str(detail)

    request_id = getattr(request.state, "request_id", None) or getattr(request.state, "correlation_id", None)

    return format_error_response(
        error_code=error_code,
        message=message if message != "None" else None,
        details=details,
        status_code=exc.status_code,
        request_id=request_id,
    )


def validation_error_to_response(request: Request, exc: RequestValidationError | ValidationError) -> JSONResponse:
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
    else:
        errors = exc.errors()

    formatted_errors: list[dict[str, Any]] = []
    for err in errors:
        formatted_errors.append(
            {
                "location": " -> ".join(str(loc) for loc in err.get("loc", [])),
                "field": err.get("loc", ["unknown"])[-1] if err.get("loc") else "unknown",
                "type": err.get("type", "unknown"),
                "message": err.get("msg", "Validation error"),
                "input": err.get("input"),
            }
        )

    request_id = getattr(request.state, "request_id", None) or getattr(request.state, "correlation_id", None)
    return format_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details=formatted_errors,
        status_code=422,
        request_id=request_id,
    )


class ErrorMiddleware:
    """ASGI middleware for unhandled exceptions."""

    def __init__(self, app: Any, debug: bool | None = None):
        self.app = app
        self.debug = debug if debug is not None else settings.DEBUG

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.exception("Unhandled exception: %s", exc)

            if self.debug:
                response_body = {
                    "error": "INTERNAL_ERROR",
                    "message": str(exc),
                    "traceback": traceback.format_exc().split("\n"),
                }
            else:
                response_body = {
                    "error": "INTERNAL_ERROR",
                    "message": "An internal server error occurred",
                }

            response_headers = [
                (b"content-type", b"application/json"),
                (b"x-error-code", b"INTERNAL_ERROR"),
            ]

            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": response_headers,
                }
            )
            import json

            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(response_body).encode("utf-8"),
                }
            )


def create_error_handler(env: str = "production"):
    """Create the appropriate error handler configuration for the environment."""

    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return http_exception_to_error(request, exc)
        if isinstance(exc, (RequestValidationError, ValidationError)):
            return validation_error_to_response(request, exc)
        if isinstance(exc, StarletteHTTPException):
            return http_exception_to_error(request, HTTPException(status_code=exc.status_code, detail=exc.detail))

        logger.exception("Unhandled exception: %s", exc)
        request_id = getattr(request.state, "request_id", None) or getattr(request.state, "correlation_id", None)

        if env != "production":
            return format_error_response(
                error_code="INTERNAL_ERROR",
                message=str(exc),
                details={"traceback": traceback.format_exc().split("\n")} if env == "development" else None,
                status_code=500,
                request_id=request_id,
            )

        return format_error_response(
            error_code="INTERNAL_ERROR",
            status_code=500,
            request_id=request_id,
        )

    return generic_error_handler
