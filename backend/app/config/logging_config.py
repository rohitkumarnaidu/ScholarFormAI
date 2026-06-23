# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Logging Configuration for Backend.

Provides structured logging with:
- Console output (INFO+)
- Rotating file handler for all logs (DEBUG+, 10 MB × 5 backups)
- Rotating file handler for errors only (ERROR+, 10 MB × 5 backups)
- Suppression of noisy third-party loggers

The log directory is created safely at import time.
setup_logging() is idempotent — safe to call multiple times.
"""

import logging
import logging.config
import logging.handlers
import os
from pathlib import Path

# ── Log directory ──────────────────────────────────────────────────────────────
# Resolve relative to this file so the path is correct regardless of cwd.
_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
LOGS_DIR = _BASE_DIR / "logs"
_bootstrap_logger = logging.getLogger(__name__)

try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except OSError as _exc:
    # Fallback to a temp directory if the preferred path is not writable
    import tempfile
    LOGS_DIR = Path(tempfile.gettempdir()) / "scholarform_logs"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    _bootstrap_logger.warning(
        "[logging_config] Could not create logs dir, using %s: %s",
        LOGS_DIR,
        _exc,
    )

# ── Logging dict config ────────────────────────────────────────────────────────
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "[request_id=%(request_id)s job_id=%(job_id)s session_id=%(session_id)s] "
                "%(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(funcName)s() - "
                "[request_id=%(request_id)s job_id=%(job_id)s session_id=%(session_id)s] "
                "%(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "context": {
            "()": "app.utils.logging_context.LogContextFilter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "filters": ["context"],
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filters": ["context"],
            "filename": str(LOGS_DIR / "app.log"),
            "maxBytes": 10_485_760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "delay": True,  # Don't open the file until first write
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filters": ["context"],
            "filename": str(LOGS_DIR / "errors.log"),
            "maxBytes": 10_485_760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
            "delay": True,
        },
    },
    "loggers": {
        # Root logger
        "": {
            "level": "INFO",
            "handlers": ["console", "file", "error_file"],
        },
        # App-specific loggers
        "app": {
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
            "propagate": False,
        },
        "app.routers": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "app.pipeline": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "app.services": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        # Suppress noisy third-party loggers
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "sqlalchemy": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False,
        },
        "httpx": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False,
        },
        "transformers": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False,
        },
        "sentence_transformers": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False,
        },
    },
}

# ── Public API ─────────────────────────────────────────────────────────────────
_logging_initialized = False


def setup_logging() -> logging.Logger:
    """
    Initialize logging configuration.

    Idempotent — safe to call multiple times (subsequent calls are no-ops).
    Returns the root app logger.
    """
    global _logging_initialized
    if _logging_initialized:
        return logging.getLogger("app")

    try:
        logging.config.dictConfig(LOGGING_CONFIG)
        _logging_initialized = True
    except Exception as exc:
        # Last-resort fallback: basic config so the app can still log
        logging.basicConfig(level=logging.INFO)
        logging.error("Failed to apply logging config: %s. Using basicConfig.", exc)

    logger = logging.getLogger("app")
    logger.info("Logging initialized. Log directory: %s", LOGS_DIR.absolute())
    return logger
