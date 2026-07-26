import os
from pathlib import Path

from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "info"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    UPLOAD_DIR: str = str(Path(__file__).parent.parent.parent / "uploads")
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    API_PREFIX: str = "/api/v1"
    VERSION: str = "1.0.0"
    DEFAULT_STYLE: str = "apa"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000

    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RATE_LIMIT_DEFAULT: int = 60
    RATE_LIMIT_WINDOW: int = 60
    CACHE_TTL_DEFAULT: int = 3600
    CACHE_BACKEND: str = "memory"
    LOG_FORMAT: str = "console"
    LOG_FILE: str | None = None
    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5
    CSP_DIRECTIVES: str | None = None
    HSTS_MAX_AGE: int = 31536000
    HSTS_INCLUDE_SUBDOMAINS: bool = True
    CORRELATION_ID_HEADER: str = "X-Correlation-ID"
    REQUEST_ID_HEADER: str = "X-Request-ID"
    PROMETHEUS_ENABLED: bool = True
    HEALTH_DISK_THRESHOLD: float = 90.0
    TEMP_FILE_TTL: int = 3600
    ENABLE_AUDIT_LOG: bool = True
    AUDIT_LOG_EXCLUDED_PATHS: list[str] = ["/health", "/ready", "/metrics"]

    model_config = ConfigDict(
        env_file=".env",
        env_prefix="AMF_",
        case_sensitive=False,
    )

    @model_validator(mode="after")
    def _enforce_production_defaults(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY:
                raise ValueError(
                    "AMF_SECRET_KEY must be set in production. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            if self.ALLOWED_ORIGINS == ["*"]:
                raise ValueError(
                    "AMF_ALLOWED_ORIGINS must be restricted in production. "
                    "Set to specific origins like: http://localhost:3000,https://yourdomain.com"
                )
        return self


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
