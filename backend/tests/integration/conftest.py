# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import os
import socket
from urllib.parse import urlparse

import pytest
import requests


def _service_reachable(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_service_reachable(url: str, timeout: float = 2.5) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False


def _docker_service_matrix() -> list[tuple[str, str, int]]:
    grobid_host = os.getenv("GROBID_HOST")
    grobid_port = os.getenv("GROBID_PORT")
    grobid_url = os.getenv("GROBID_URL") or os.getenv("GROBID_BASE_URL")
    if not grobid_host:
        if grobid_url:
            parsed = urlparse(grobid_url if "://" in grobid_url else f"http://{grobid_url}")
            if parsed.hostname:
                grobid_host = parsed.hostname
                grobid_port = str(parsed.port or (443 if parsed.scheme == "https" else 80))

    return [
        ("Redis", os.getenv("REDIS_HOST", "127.0.0.1"), int(os.getenv("REDIS_PORT", "6379"))),
        ("GROBID", grobid_host or "127.0.0.1", int(grobid_port or "8070")),
    ]


@pytest.fixture(autouse=True)
def ensure_docker_services_available():
    missing = []

    for name, host, port in _docker_service_matrix():
        if name != "GROBID":
            if not _service_reachable(host, port):
                missing.append(name)
            continue

        grobid_url = os.getenv("GROBID_URL") or os.getenv("GROBID_BASE_URL")
        if grobid_url:
            if not _http_service_reachable(f"{grobid_url.rstrip('/')}/api/isalive"):
                missing.append(name)
        elif not _service_reachable(host, port):
            missing.append(name)

    if missing:
        pytest.skip(f"Service {', '.join(missing)} not available")


def pytest_collection_modifyitems(items):
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        if "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
