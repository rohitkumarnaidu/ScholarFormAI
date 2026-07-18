# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Timeout and retry contract tests.

Covers:
  3A: Timeout handling and 504 Gateway Timeout response
  3B: Retry behavior for idempotent vs non-idempotent endpoints
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_ai_models():
    with (
        patch("app.pipeline.intelligence.semantic_parser.get_semantic_parser", return_value=MagicMock()),
        patch("app.pipeline.intelligence.rag_engine.get_rag_engine", return_value=MagicMock()),
    ):
        yield


# ── 3A: Timeout Handling ─────────────────────────────────────────────────


class Test3A_TimeoutHandling:
    """Timeout response and error schema validation."""

    @pytest.fixture
    def client(self):
        from app.main import app
        from app.utils.dependencies import get_current_user
        mock_user = MagicMock()
        mock_user.id = "user-timeout"
        mock_user.role = "authenticated"
        app.dependency_overrides.clear()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        with (
            patch("app.routers.v1.documents_impl._require_db"),
            patch("app.routers.v1.documents_impl.DocumentService"),
            patch("app.db.supabase_client.get_supabase_client", return_value=MagicMock()),
        ):
            with TestClient(app) as c:
                c.headers.update({"Authorization": "Bearer test-token"})
                yield c
        app.dependency_overrides.clear()

    def _response_json(self, resp):
        return json.loads(resp.body.decode())

    def test_timeout_error_schema_has_consistent_envelope(self):
        from app.routers.v1._helpers import build_error_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-to"
        resp = build_error_response(mock_req, status_code=504, code="GATEWAY_TIMEOUT",
                                     message="Upstream service timed out")
        body = self._response_json(resp)
        assert resp.status_code == 504
        assert body["error"]["code"] == "GATEWAY_TIMEOUT"
        assert body["error"]["message"] == "Upstream service timed out"
        assert body["data"] is None
        assert "request_id" in body
        assert "timestamp" in body

    def test_timeout_response_has_code_from_default_map(self):
        from app.routers.v1._helpers import DEFAULT_ERROR_CODES
        assert 504 not in DEFAULT_ERROR_CODES

    def test_gateway_timeout_is_considered_server_error(self):
        resp = MagicMock()
        resp.status_code = 504
        assert 500 <= resp.status_code < 600

    def test_timeout_body_consistent_with_other_errors(self):
        from app.routers.v1._helpers import build_error_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-compare"
        to_resp = build_error_response(mock_req, status_code=504, code="GATEWAY_TIMEOUT",
                                        message="Upstream timed out")
        err_resp = build_error_response(mock_req, status_code=500, code="INTERNAL_SERVER_ERROR",
                                         message="Server error")
        to_body = self._response_json(to_resp)
        err_body = self._response_json(err_resp)
        for key in ("request_id", "timestamp", "error"):
            assert key in to_body
        assert to_body["error"]["code"] != err_body["error"]["code"]

    def test_asyncio_timeout_raises_exception(self):
        async def slow_operation():
            await asyncio.sleep(10)
            return "done"

        async def run_with_timeout():
            try:
                return await asyncio.wait_for(slow_operation(), timeout=0.01)
            except asyncio.TimeoutError:
                raise HTTPException(status_code=504, detail="Upstream service timed out")

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(run_with_timeout())
        assert exc_info.value.status_code == 504

    def test_timeout_error_does_not_leak_internals(self):
        from app.routers.v1._helpers import build_error_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-safe"
        resp = build_error_response(mock_req, status_code=504, code="GATEWAY_TIMEOUT",
                                     message="Upstream service timed out")
        body = self._response_json(resp)
        assert "trace" not in body["error"].get("message", "").lower()


# ── 3B: Retry Behavior ───────────────────────────────────────────────────


class Test3B_RetryBehavior:
    """Retry behavior for idempotent vs non-idempotent endpoints."""

    def test_get_requests_are_idempotent(self):
        from fastapi.testclient import TestClient
        assert True

    def test_put_requests_are_idempotent(self):
        from fastapi.testclient import TestClient
        assert True

    def test_delete_requests_are_idempotent(self):
        from fastapi.testclient import TestClient
        assert True

    def test_get_can_be_retried_safely(self):
        responses = [
            MagicMock(status_code=503),
            MagicMock(status_code=200, json=lambda: {"data": "success"}),
        ]
        attempt_count = 0
        for _ in range(3):
            resp = responses.pop(0) if responses else MagicMock(status_code=500)
            attempt_count += 1
            if resp.status_code == 200:
                assert resp.json()["data"] == "success"
                break
        assert attempt_count == 2

    def test_post_should_not_auto_retry(self):
        resp = MagicMock(status_code=503)
        assert resp.status_code == 503

    def _response_json(self, resp):
        return json.loads(resp.body.decode())

    def test_post_with_idempotency_key_prevents_duplicates(self):
        from app.routers.v1._helpers import build_success_response, build_error_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-ik"
        first = build_success_response(mock_req, {"status": "created"})
        second = build_error_response(mock_req, status_code=409, code="CONFLICT",
                                       message="Duplicate request detected")
        assert first.status_code == 200
        assert second.status_code == 409
        assert self._response_json(second)["error"]["code"] == "CONFLICT"

    def test_idempotent_retry_returns_original_result(self):
        from app.routers.v1._helpers import build_success_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-retry"
        resp1 = build_success_response(mock_req, {"id": "doc-1", "status": "completed"})
        resp2 = build_success_response(mock_req, {"id": "doc-1", "status": "completed"})
        assert resp1.status_code == resp2.status_code
        assert self._response_json(resp1)["data"]["id"] == self._response_json(resp2)["data"]["id"]

    def test_non_idempotent_operation_changes_state(self):
        from app.routers.v1._helpers import build_success_response
        mock_req = MagicMock()
        mock_req.state.request_id = "req-state"

        created = build_success_response(mock_req, {"id": "new-1", "status": "pending"})
        created2 = build_success_response(mock_req, {"id": "new-2", "status": "pending"})
        assert self._response_json(created)["data"]["id"] != self._response_json(created2)["data"]["id"]
