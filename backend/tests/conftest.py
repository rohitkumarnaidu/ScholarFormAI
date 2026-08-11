# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
conftest.py — shared pytest fixtures for ScholarForm AI backend tests.
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest
import requests

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if Path.cwd() != BACKEND_ROOT:
    os.chdir(BACKEND_ROOT)

os.environ["AMF_ENVIRONMENT"] = "test"
os.environ["AMF_SECRET_KEY"] = "test-secret-key"
os.environ["ENCRYPTION_KEY"] = "a2geXVIrEQu5-kHc2k8Peps0EYf9sEyzIo7A9bdO8sU="
os.environ["SUPABASE_URL"] = "http://localhost:8000"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_anon_key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_service_key"
os.environ["SUPABASE_DB_URL"] = "postgresql://postgres:postgres@localhost:5432/postgres"
os.environ["SUPABASE_JWT_SECRET"] = "dummy-jwt-secret-key"

import contextlib

from app.services import health_checks


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


def _integration_service_status() -> list[str]:
    missing: list[str] = []
    grobid_host = os.getenv("GROBID_HOST")
    grobid_port = os.getenv("GROBID_PORT")
    grobid_url = os.getenv("GROBID_URL") or os.getenv("GROBID_BASE_URL")
    if not grobid_host and grobid_url:
        parsed = urlparse(grobid_url if "://" in grobid_url else f"http://{grobid_url}")
        if parsed.hostname:
            grobid_host = parsed.hostname
            grobid_port = str(parsed.port or (443 if parsed.scheme == "https" else 80))

    redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    if not _service_reachable(redis_host, redis_port):
        missing.append("Redis")

    if grobid_url:
        health_url = f"{grobid_url.rstrip('/')}/api/isalive"
        if not _http_service_reachable(health_url):
            missing.append("GROBID")
    elif not _service_reachable(grobid_host or "127.0.0.1", int(grobid_port or "8070")):
        missing.append("GROBID")

    return missing


@pytest.fixture(autouse=True)
def skip_integration_when_services_unavailable(request):
    if "integration" not in request.keywords:
        return
    missing = _integration_service_status()
    if missing:
        pytest.skip(f"Service {', '.join(missing)} not available")


@pytest.fixture(autouse=True)
def mock_redis(request):
    """Mock Redis globally for all tests. Gracefully skips if router imports fail."""
    try:
        from app.routers.v1.stream import _pubsub  # noqa: F401
    except (ImportError, TypeError):
        yield {}
        return
    with patch("app.routers.v1.stream._pubsub.publish", new_callable=AsyncMock) as mock_stream_publish:
        with patch("app.middleware.rate_limit.redis") as mock_limit:
            with patch("app.cache.redis_cache.redis.Redis") as mock_cache:
                mock_limit.return_value = MagicMock()
                mock_cache.return_value = MagicMock()
                yield {
                    "stream_publish": mock_stream_publish,
                    "rate_limit": mock_limit,
                    "cache": mock_cache,
                }


def _walk_middleware_chain(root):
    """Yield middleware instances by walking Starlette's nested `.app` chain."""
    current = root
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = getattr(current, "app", None)


def _reset_slowapi_storage(app):
    """Best-effort reset for SlowAPI in-memory counters between tests."""
    limiter = getattr(getattr(app, "state", object()), "limiter", None)
    if limiter is None:
        return

    storage = getattr(limiter, "_storage", None) or getattr(limiter, "storage", None)
    if storage is None:
        return

    for method_name in ("reset", "clear"):
        method = getattr(storage, method_name, None)
        if callable(method):
            try:
                method()
                return
            except TypeError:
                # Some backends require args; fallback to dict-clearing below.
                pass

    for attr_name in ("storage", "events", "expirations"):
        candidate = getattr(storage, attr_name, None)
        if hasattr(candidate, "clear"):
            candidate.clear()


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """
    Prevent cross-test contamination from app-level rate limiter middleware state.

    Gracefully skipped if the app module cannot be loaded.
    """
    try:
        from app.main import app
    except (ImportError, TypeError):
        yield
        return

    # Build middleware stack lazily if needed so we can access middleware instances.
    if app.middleware_stack is None:
        app.middleware_stack = app.build_middleware_stack()

    for middleware in _walk_middleware_chain(app.middleware_stack):
        request_counts = getattr(middleware, "request_counts", None)
        if hasattr(request_counts, "clear"):
            request_counts.clear()

        upload_counts = getattr(middleware, "upload_request_counts", None)
        if hasattr(upload_counts, "clear"):
            upload_counts.clear()

        tier_counts = getattr(middleware, "_memory_counts", None)
        if hasattr(tier_counts, "clear"):
            tier_counts.clear()

    _reset_slowapi_storage(app)
    yield
    _reset_slowapi_storage(app)


@pytest.fixture(autouse=True)
def reset_health_check_caches():
    """Avoid cross-test contamination from cached /health and /ready payloads."""
    with contextlib.suppress(Exception):
        health_checks._reset_readiness_cache_for_tests()
    yield
    with contextlib.suppress(Exception):
        health_checks._reset_readiness_cache_for_tests()


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    """Ensure FastAPI dependency overrides are cleared before and after each test."""
    try:
        from app.main import app
    except (ImportError, TypeError):
        yield
        return
    
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


from app.models import (
    Block,
    BlockType,
    DocumentMetadata,
    PipelineDocument,
    Reference,
    ReferenceType,
)

# ── Document fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def minimal_doc() -> PipelineDocument:
    """Bare-minimum PipelineDocument with title + one body block."""
    doc = PipelineDocument(
        document_id="test-doc-001",
        metadata=DocumentMetadata(
            title="Test Manuscript",
            authors=["Jane Doe"],
            abstract="A short abstract.",
        ),
    )
    doc.blocks = [
        Block(block_id="b1", index=1, block_type=BlockType.TITLE,  text="Test Manuscript"),
        Block(block_id="b2", index=2, block_type=BlockType.HEADING_1, text="Introduction"),
        Block(block_id="b3", index=3, block_type=BlockType.BODY,   text="Body content here."),
    ]
    return doc


@pytest.fixture
def full_doc(minimal_doc: PipelineDocument) -> PipelineDocument:
    """PipelineDocument with metadata, blocks, and a reference."""
    minimal_doc.metadata.keywords = ["formatting", "test"]
    minimal_doc.metadata.affiliations = ["Test University"]
    ref = Reference(
        reference_id="ref_1",
        citation_key="ref1",
        raw_text="[1] J. Doe, Testing, 2024.",
        reference_type=ReferenceType.JOURNAL_ARTICLE,
        authors=["Doe, J."],
        title="Testing",
        year=2024,
        index=0,
        formatted_text="[1] J. Doe, 'Testing,' 2024.",
    )
    minimal_doc.references = [ref]
    minimal_doc.blocks.append(
        Block(block_id="b4", index=4, block_type=BlockType.REFERENCE_ENTRY, text="[1] J. Doe, Testing, 2024.")
    )
    return minimal_doc






import fastapi.routing
old_merge = fastapi.routing._merge_lifespan_context
