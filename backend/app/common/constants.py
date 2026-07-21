# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

ERROR_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_SERVER_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}

PERSONA_PATH_MAP: dict[str, str] = {
    "/api/v1/documents": "formatter",
    "/api/v1/generator": "authoring",
    "/api/v1/synthesis": "synthesis",
    "/api/v1/billing": "billing",
    "/api/v1/templates": "templates",
}

METRIC_LABELS: dict[str, dict[str, str]] = {
    "personas": {
        "formatter": "formatter",
        "authoring": "authoring",
        "synthesis": "synthesis",
        "billing": "billing",
        "templates": "templates",
        "platform": "platform",
    },
    "outcomes": {
        "success": "success",
        "error": "error",
    },
}

ERROR_CODE_TO_HTTP: dict[str, int] = {v: k for k, v in ERROR_CODES.items()}

SERVICE_HEALTH_DEFAULTS: dict[str, str] = {
    "grobid": "/api/isalive",
    "docling": "/",
    "ocr": "/",
    "docx_converter": "/",
    "nougat": "/",
    "scibert": "/",
}
