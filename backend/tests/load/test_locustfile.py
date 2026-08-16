# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Pytest wrapper for Locust load tests.

Validates that the locustfile is importable and well-formed,
and provides a smoke-test that skips without a running backend.

Run full load tests with: locust -f tests/load/locustfile.py --headless -u 10 -t 30s
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

BASE_URL = "http://127.0.0.1:8000"

# Detect locust availability early (gevent/SSL incompatibility on Python 3.14+)
_LOCUST_AVAILABLE = False
_LOCUST_ERROR = None
try:
    from locust import HttpUser, User

    _LOCUST_AVAILABLE = True
except RecursionError as exc:
    _LOCUST_ERROR = f"Locust incompatible with this Python version (gevent/SSL conflict): {exc}"
except Exception as exc:
    _LOCUST_ERROR = f"Locust not available: {exc}"


def _locustfile_available():
    """Check if the locustfile module can be loaded."""
    if not _LOCUST_AVAILABLE:
        return False
    try:
        from tests.load import locustfile

        return locustfile is not None
    except Exception:
        return False


def _backend_reachable(host: str = "127.0.0.1", port: int = 8000, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture
def locustfile_module():
    """Provide the locustfile module, skipping if unavailable."""
    if not _LOCUST_AVAILABLE:
        pytest.skip(_LOCUST_ERROR or "Locust not available")
    from tests.load import locustfile

    return locustfile


class TestLocustfileStructure:
    """Validate locustfile.py is importable and well-formed."""

    def test_locustfile_importable(self, locustfile_module):
        """Verify locustfile can be imported without errors."""
        assert locustfile_module is not None

    def test_user_classes_defined(self, locustfile_module):
        """Verify all expected Locust User classes exist."""
        assert hasattr(locustfile_module, "UploadUser")
        assert hasattr(locustfile_module, "StatusPollUser")
        assert hasattr(locustfile_module, "TemplatesUser")
        assert hasattr(locustfile_module, "PreviewWebSocketUser")

    def test_user_classes_inherit_correctly(self, locustfile_module):
        """Verify User classes inherit from proper Locust base classes."""
        assert issubclass(locustfile_module.UploadUser, HttpUser)
        assert issubclass(locustfile_module.StatusPollUser, HttpUser)
        assert issubclass(locustfile_module.TemplatesUser, HttpUser)
        assert issubclass(locustfile_module.PreviewWebSocketUser, User)

    def test_slo_enforcement_hook_exists(self, locustfile_module):
        """Verify the SLO enforcement event hook is defined."""
        assert hasattr(locustfile_module, "enforce_slo_thresholds")

    def test_task_methods_exist(self, locustfile_module):
        """Verify each User class has at least one @task method."""
        assert hasattr(locustfile_module.UploadUser, "upload_document")
        assert hasattr(locustfile_module.StatusPollUser, "poll_status")
        assert hasattr(locustfile_module.TemplatesUser, "list_templates")
        assert hasattr(locustfile_module.PreviewWebSocketUser, "preview_ws_roundtrip")


class TestLocustSmokeBackend:
    """Quick smoke tests against a running backend (skips if unavailable)."""

    @pytest.fixture(autouse=True)
    def skip_without_backend(self):
        if not _backend_reachable():
            pytest.skip(f"Backend not reachable at {BASE_URL}")

    def test_health_endpoint(self):
        """Smoke test: /health returns 200."""
        import requests

        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        assert resp.status_code == 200

    def test_templates_endpoint(self):
        """Smoke test: /api/v1/templates returns 200."""
        import requests

        resp = requests.get(f"{BASE_URL}/api/v1/templates", timeout=5)
        assert resp.status_code == 200
