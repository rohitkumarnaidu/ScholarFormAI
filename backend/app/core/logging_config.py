import json
import logging
import logging.config
import logging.handlers
import re
import threading
from datetime import UTC, datetime
from pathlib import Path
from re import Pattern
from typing import Any

SENSITIVE_PATTERNS: list[Pattern] = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"(?i)(api[_-]?key|apikey|secret|password|token|auth|credential)[:=]\s*['\"]?\S+['\"]?"),
    re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b"),
]

_log_context = threading.local()


def set_log_context(**kwargs: Any) -> None:
    for key, value in kwargs.items():
        setattr(_log_context, key, value)


def clear_log_context() -> None:
    if hasattr(_log_context, "__dict__"):
        _log_context.__dict__.clear()


def get_log_context() -> dict[str, Any]:
    return getattr(_log_context, "__dict__", {}).copy()


def redact_sensitive(value: str) -> str:
    if not isinstance(value, str):
        return value
    for pattern in SENSITIVE_PATTERNS:
        value = pattern.sub("[redacted]", value)
    return value


def redact_dict(data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    if depth > 5:
        return {"[redacted]": "max_depth"}
    result: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(
            s in key_lower
            for s in (
                "api_key",
                "apikey",
                "secret",
                "password",
                "token",
                "auth",
                "credential",
                "authorization",
            )
        ):
            result[key] = "[redacted]"
        elif isinstance(value, dict):
            result[key] = redact_dict(value, depth + 1)
        elif isinstance(value, str):
            result[key] = redact_sensitive(value)
        elif isinstance(value, list):
            result[key] = [
                redact_dict(item, depth + 1)
                if isinstance(item, dict)
                else redact_sensitive(item)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production use."""

    def __init__(self, include_context: bool = True, redact: bool = True):
        super().__init__()
        self.include_context = include_context
        self.redact = redact

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "pid": record.process,
            "thread": record.threadName,
        }

        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
            }

        if self.include_context:
            context = get_log_context()
            if context:
                log_entry["context"] = context

        if self.redact:
            log_entry = redact_dict(log_entry)

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Colorized console log formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        level_color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        message = record.getMessage()
        if self._needs_redaction(record):
            message = redact_sensitive(message)
        log_line = (
            f"{timestamp} | {level_color}{record.levelname:<8s}{self.RESET} | "
            f"{record.name}:{record.funcName}:{record.lineno} | {message}"
        )
        if record.exc_info and record.exc_info[0]:
            log_line += f"\n{self.formatException(record.exc_info)}"
        return log_line

    def _needs_redaction(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage().lower()
        return any(s in msg for s in ("email", "password", "secret", "token", "api_key", "apikey"))


def setup_logging(
    env: str = "development",
    log_level: str = "INFO",
    log_dir: str | None = None,
    json_format: bool = False,
    enable_audit_log: bool = True,
) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json" if json_format or env == "production" else "console",
            "level": level,
        },
    }

    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path / "amf.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
            "level": level,
        }
        handlers["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_path / "error.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "json",
            "level": logging.ERROR,
        }

    if enable_audit_log:
        audit_handlers: dict[str, Any] = {}
        if log_dir:
            audit_log_path = Path(log_dir)
            audit_handlers["audit_file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(audit_log_path / "audit.log"),
                "maxBytes": 50 * 1024 * 1024,
                "backupCount": 10,
                "formatter": "json",
                "level": logging.INFO,
            }
        if audit_handlers:
            handlers["audit"] = audit_handlers["audit_file"]

    log_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter,
                "include_context": True,
                "redact": True,
            },
            "console": {
                "()": ConsoleFormatter,
            },
        },
        "handlers": handlers,
        "root": {
            "level": level,
            "handlers": [h for h in handlers if h != "audit"],
        },
        "loggers": {
            "uvicorn": {"level": logging.WARNING, "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": logging.WARNING, "handlers": [], "propagate": False},
            "uvicorn.error": {
                "level": logging.WARNING,
                "handlers": ["console"],
                "propagate": False,
            },
            "audit": {
                "level": logging.INFO,
                "handlers": [h for h in handlers if h == "audit"] or ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(log_config)
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured: env=%s, level=%s, json=%s",
        env,
        log_level,
        json_format or env == "production",
    )
