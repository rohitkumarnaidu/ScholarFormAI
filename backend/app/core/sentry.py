import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SentryConfig:
    dsn: str = ""
    environment: str = "development"
    traces_sample_rate: float = 0.1
    profiles_sample_rate: float = 0.0
    enable_tracing: bool = True
    max_breadcrumbs: int = 50
    send_default_pii: bool = False
    release: str | None = None
    server_name: str | None = None
    ignore_errors: tuple = (
        "HTTPException",
        "ValidationError",
        "StyleNotFoundError",
        "RateLimitError",
    )
    in_app_include: tuple = ("app.",)
    attach_stacktrace: bool = True
    debug: bool = False


_sentry_initialized = False


def init_sentry(config: SentryConfig | None = None) -> bool:
    global _sentry_initialized
    if _sentry_initialized:
        logger.debug("Sentry already initialized")
        return True

    cfg = config or SentryConfig()

    if not cfg.dsn:
        logger.info("Sentry DSN not configured, skipping initialization")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.excepthook import ExcepthookIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=cfg.dsn,
            environment=cfg.environment,
            traces_sample_rate=cfg.traces_sample_rate,
            profiles_sample_rate=cfg.profiles_sample_rate,
            enable_tracing=cfg.enable_tracing,
            max_breadcrumbs=cfg.max_breadcrumbs,
            send_default_pii=cfg.send_default_pii,
            release=cfg.release,
            server_name=cfg.server_name,
            attach_stacktrace=cfg.attach_stacktrace,
            debug=cfg.debug,
            integrations=[
                StarletteIntegration(
                    transaction_style="endpoint",
                    failed_request_status_codes={*range(400, 600)},
                ),
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=logging.INFO, event_level=logging.WARNING),
                ExcepthookIntegration(),
            ],
            ignore_errors=cfg.ignore_errors,
            in_app_include=cfg.in_app_include,
            before_send=_before_send,
            before_send_transaction=_before_send_transaction,
        )

        _sentry_initialized = True
        logger.info(
            "Sentry initialized for environment '%s' with sample rate %.2f",
            cfg.environment,
            cfg.traces_sample_rate,
        )
        return True

    except ImportError:
        logger.warning("sentry-sdk not installed. Install with: pip install sentry-sdk")
        return False
    except Exception as exc:
        logger.error("Failed to initialize Sentry: %s", exc)
        return False


def _before_send(event, hint) -> dict | None:
    if event.get("level") == "debug":
        return None

    exc_info = hint.get("exc_info")
    if exc_info:
        exc_type = exc_info[0].__name__ if exc_info[0] else ""
        if exc_type in (
            "HTTPException",
            "ValidationError",
            "StyleNotFoundError",
            "RateLimitError",
            "ManuscriptTooLargeError",
            "UnsupportedFormatError",
        ):
            return None

    request_info = event.get("request", {})
    if "headers" in request_info:
        headers = request_info["headers"]
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in (
                "authorization",
                "cookie",
                "x-api-key",
                "proxy-authorization",
                "set-cookie",
            ):
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = value
        event["request"]["headers"] = sanitized

    return event


def _before_send_transaction(event) -> dict | None:
    if event.get("transaction_info", {}).get("source") == "url":
        event["request"] = {"url": event.get("request", {}).get("url", "")}
    return event


def sentry_initialized() -> bool:
    return _sentry_initialized
