from typing import Any


class AMFError(Exception):
    def __init__(
        self, code: str, message: str, status_code: int = 500, details: dict[str, Any] | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class FormattingError(AMFError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("FORMATTING_ERROR", message, status_code=422, details=details)


class ValidationError(AMFError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__("VALIDATION_ERROR", message, status_code=400, details=details)


class StyleNotFoundError(AMFError):
    def __init__(self, style_id: str):
        super().__init__(
            "STYLE_NOT_FOUND",
            f"Formatting style '{style_id}' is not supported",
            status_code=404,
        )


class ManuscriptTooLargeError(AMFError):
    def __init__(self, size: int, max_size: int):
        super().__init__(
            "MANUSCRIPT_TOO_LARGE",
            f"Manuscript size ({size} bytes) exceeds maximum allowed ({max_size} bytes)",
            status_code=413,
        )


class UnsupportedFormatError(AMFError):
    def __init__(self, fmt: str):
        super().__init__(
            "UNSUPPORTED_FORMAT",
            f"Input format '{fmt}' is not supported",
            status_code=400,
        )


class RateLimitError(AMFError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            "RATE_LIMIT_EXCEEDED",
            f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=429,
            details={"retry_after": retry_after},
        )
