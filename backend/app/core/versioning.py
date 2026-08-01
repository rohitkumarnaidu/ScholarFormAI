import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from re import Pattern
from typing import Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__

logger = logging.getLogger(__name__)

VERSION_PATTERN: Pattern = re.compile(r"^\d+\.\d+(\.\d+)?$")


@dataclass
class APIVersion:
    major: int
    minor: int
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, APIVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: "APIVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: "APIVersion") -> bool:
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: "APIVersion") -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: "APIVersion") -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    @classmethod
    def parse(cls, version_str: str) -> "APIVersion":
        if not VERSION_PATTERN.match(version_str):
            raise ValueError(f"Invalid version format: {version_str}. Expected 'major.minor.patch'")
        parts = version_str.split(".")
        major, minor = int(parts[0]), int(parts[1])
        patch = int(parts[2]) if len(parts) > 2 else 0
        return cls(major=major, minor=minor, patch=patch)

    @classmethod
    def from_path(cls, path: str) -> Optional["APIVersion"]:
        match = re.search(r"/v(\d+)(?:\.(\d+))?", path)
        if not match:
            return None
        major = int(match.group(1))
        minor = int(match.group(2)) if match.group(2) else 0
        return cls(major=major, minor=minor)


@dataclass
class VersionInfo:
    current: APIVersion = field(default_factory=lambda: APIVersion.parse(__version__.split("-")[0]))
    supported: list[APIVersion] = field(default_factory=lambda: [APIVersion(major=1, minor=0)])
    deprecated: list[APIVersion] = field(default_factory=list)
    sunset: dict[str, datetime] = field(default_factory=dict)

    def is_supported(self, version: APIVersion) -> bool:
        return any(version == v for v in self.supported)

    def is_deprecated(self, version: APIVersion) -> bool:
        return any(version == v for v in self.deprecated)

    def get_sunset_date(self, version: APIVersion) -> datetime | None:
        return self.sunset.get(str(version))

    def add_deprecation(self, version: APIVersion, sunset_date: datetime | None = None) -> None:
        if version not in self.deprecated:
            self.deprecated.append(version)
        if sunset_date:
            self.sunset[str(version)] = sunset_date


version_info = VersionInfo()


def get_api_version(request: Request) -> APIVersion | None:
    accept_header = request.headers.get("Accept", "")
    accept_match = re.search(r"version=(\d+\.\d+(?:\.\d+)?)", accept_header)
    if accept_match:
        try:
            return APIVersion.parse(accept_match.group(1))
        except ValueError:
            pass  # intentionally ignored

    custom_header = request.headers.get("X-API-Version", "")
    if custom_header:
        try:
            return APIVersion.parse(custom_header)
        except ValueError:
            pass  # intentionally ignored

    return APIVersion.from_path(request.url.path)


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning, deprecation warnings, and sunset headers."""

    def __init__(
        self,
        app: Any,
        version_info: VersionInfo | None = None,
        default_version: APIVersion | None = None,
    ):
        super().__init__(app)
        self.version_info = version_info or globals().get("version_info", VersionInfo())
        self.default_version = default_version or APIVersion(major=1, minor=0)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path.startswith("/api/"):
            request_version = get_api_version(request)
            if request_version is None:
                request_version = self.default_version

            request.state.api_version = request_version
            response = await call_next(request)

            response.headers["X-API-Version"] = str(request_version)
            response.headers["X-API-Latest-Version"] = str(self.version_info.current)

            if self.version_info.is_deprecated(request_version):
                response.headers["X-API-Deprecated"] = "true"
                response.headers["X-API-Deprecation-Message"] = (
                    f"API version {request_version} is deprecated. "
                    f"Please migrate to version {self.version_info.current}."
                )
                sunset_date = self.version_info.get_sunset_date(request_version)
                if sunset_date:
                    response.headers["Sunset"] = sunset_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                    response.headers["X-API-Sunset-Date"] = sunset_date.isoformat()

            if request_version < self.version_info.current:
                response.headers["X-API-Upgrade"] = f"version={self.version_info.current}"
        else:
            response = await call_next(request)

        return response


def require_min_version(min_version: str) -> Callable:
    """Dependency to enforce minimum API version for an endpoint."""

    required = APIVersion.parse(min_version)

    def version_dependency(request: Request) -> None:
        client_version: APIVersion | None = getattr(request.state, "api_version", None)
        if client_version is None:
            client_version = APIVersion.from_path(request.url.path) or APIVersion(major=1, minor=0)
        if client_version < required:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=426,
                detail={
                    "error": "UPGRADE_REQUIRED",
                    "message": (
                        f"API version {client_version} is too old. "
                        f"Minimum required version is {required}. "
                        f"Please upgrade to version {version_info.current}."
                    ),
                    "current_version": str(client_version),
                    "minimum_version": str(required),
                    "latest_version": str(version_info.current),
                },
            )

    return version_dependency


def deprecation_header(removal_date: str | None = None) -> Callable:
    """Decorator to add deprecation warnings to specific endpoints."""

    def decorator(func: Callable) -> Callable:
        import functools
        import inspect

        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                response = await func(*args, **kwargs)
                if isinstance(response, Response):
                    response.headers["X-API-Deprecated-Endpoint"] = "true"
                    if removal_date:
                        response.headers["X-API-Removal-Date"] = removal_date
                return response

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                response = func(*args, **kwargs)
                if isinstance(response, Response):
                    response.headers["X-API-Deprecated-Endpoint"] = "true"
                    if removal_date:
                        response.headers["X-API-Removal-Date"] = removal_date
                return response

            return sync_wrapper

    return decorator


def version_negotiation(request: Request) -> APIVersion:
    """Determine the best API version based on request headers and URL."""
    version = get_api_version(request)
    if version is None:
        return APIVersion(major=1, minor=0)
    if version_info.is_supported(version):
        return version
    return version_info.current
