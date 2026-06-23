# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest

from app.main import _normalize_request_path, _should_bypass_https_redirect


@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/health/",
        "/ready",
        "/ready/",
        "/api/v1/health",
        "/api/v1/health/live",
        "/api/v1/health/live/",
        "api/v1/health/ready",
        "/api/v1/health/admin",
    ],
)
def test_health_paths_bypass_https_redirect(path: str) -> None:
    assert _should_bypass_https_redirect(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/docs",
        "/redoc",
        "/api/v1/documents",
        "/api/v1/generator/sessions",
        "/healthz",
    ],
)
def test_non_health_paths_do_not_bypass_https_redirect(path: str) -> None:
    assert _should_bypass_https_redirect(path) is False


def test_normalize_request_path_handles_empty_values() -> None:
    assert _normalize_request_path("") == "/"
    assert _normalize_request_path(None) == "/"
