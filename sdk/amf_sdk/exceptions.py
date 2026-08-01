from typing import Any


class AMFError(Exception):
    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class AMFConnectionError(AMFError):
    def __init__(self, message: str = "Failed to connect to AMF API"):
        super().__init__(message, status_code=503)


class AMFTimeoutError(AMFError):
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, status_code=504)


class AMFValidationError(AMFError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=400, details=details)


class AMFFormattingError(AMFError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=422, details=details)


class AMFAuthenticationError(AMFError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AMFNotFoundError(AMFError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class AMFRateLimitError(AMFError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after} seconds",
            status_code=429,
            details={"retry_after": retry_after},
        )
