# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""Idempotency key tests — duplicate prevention, TTL, malformed keys, endpoint coverage."""

from __future__ import annotations

import json
import time
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient


# ── Idempotency store (in-memory, simulates the cache layer) ───────────────────

class _IdempotencyStore:
    def __init__(self):
        self._store: dict[str, tuple[float, dict]] = {}
        self._ttl = 60

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, payload = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return payload

    def set(self, key: str, payload: dict, ttl: int | None = None):
        self._store[key] = (time.time() + (ttl or self._ttl), payload)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def clear_expired(self):
        now = time.time()
        expired = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]


# ── Idempotency decorator / helper (simulates backend idempotency logic) ───────

def _idempotent_handler(store: _IdempotencyStore, key: str, request_payload: dict):
    """Simulate the idempotency check that endpoint logic would use."""
    existing = store.get(key)
    if existing is not None:
        if existing["payload"] != request_payload:
            raise HTTPException(
                status_code=422,
                detail="Idempotency key already used with a different request body",
            )
        return existing["response"]
    return None


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestIdempotencyKey:
    @pytest.fixture
    def store(self):
        return _IdempotencyStore()

    @pytest.fixture
    def app(self):
        _app = FastAPI()
        store = _IdempotencyStore()

        @_app.post("/upload")
        async def upload(request: dict):
            idem_key = request.get("idempotency_key", "")
            payload = {k: v for k, v in request.items() if k != "idempotency_key"}
            existing = store.get(idem_key)
            if existing is not None:
                if existing["payload"] != payload:
                    raise HTTPException(
                        status_code=422,
                        detail="Idempotency key already used with a different request body",
                    )
                return existing["response"]
            result = {"status": "created", "document_id": "doc-new"}
            store.set(idem_key, {"payload": payload, "response": result})
            return result

        _app.store = store
        return _app

    def test_prevents_duplicate_creation(self):
        """Same idempotency key + same payload returns cached result, not duplicate."""
        store = _IdempotencyStore()
        key = "idem-001"
        payload = {"title": "Manuscript", "idempotency_key": key}
        response = {"status": "created", "document_id": "doc-001"}
        store.set(key, {"payload": {"title": "Manuscript"}, "response": response})

        result = _idempotent_handler(store, key, {"title": "Manuscript"})
        assert result == response

    def test_same_key_same_payload_returns_same(self):
        """Same idempotency key with identical payload returns identical result."""
        store = _IdempotencyStore()
        key = "idem-002"
        payload = {"title": "Paper", "idempotency_key": key}
        response = {"status": "created", "document_id": "doc-002"}
        store.set(key, {"payload": {"title": "Paper"}, "response": response})

        first = _idempotent_handler(store, key, {"title": "Paper"})
        second = _idempotent_handler(store, key, {"title": "Paper"})
        assert first == response
        assert second == response

    def test_same_key_different_payload_rejected(self):
        """Same idempotency key with a different request body is rejected with 422."""
        store = _IdempotencyStore()
        key = "idem-003"
        store.set(key, {"payload": {"title": "Original"}, "response": {"status": "created"}})

        with pytest.raises(HTTPException) as exc:
            _idempotent_handler(store, key, {"title": "Different"})
        assert exc.value.status_code == 422

    def test_ttl_enforcement(self):
        """Expired idempotency key is treated as non-existent."""
        store = _IdempotencyStore()
        key = "idem-004"
        store._ttl = 0.01
        store.set(key, {"payload": {"title": "Temp"}, "response": {"status": "created"}}, ttl=0.01)
        time.sleep(0.02)
        assert store.exists(key) is False

    def test_no_key_allowed_through(self):
        """Request without idempotency-key header should proceed normally."""
        store = _IdempotencyStore()
        key = ""
        payload = {"title": "No-Key"}
        result = _idempotent_handler(store, key, payload)
        assert result is None

    def test_expired_key_allows_new_request(self):
        """After key expires, a new request with that key succeeds."""
        store = _IdempotencyStore()
        key = "idem-expired"
        store.set(key, {"payload": {"title": "Old"}, "response": {"status": "old"}}, ttl=0.01)
        time.sleep(0.02)
        result = _idempotent_handler(store, key, {"title": "New"})
        assert result is None

    def test_malformed_key_handled_gracefully(self):
        """Malformed idempotency keys should not crash the handler."""
        store = _IdempotencyStore()
        malformed_keys = ["", None, "   ", "!@#$%^&*()"]
        for key in malformed_keys:
            if not key or key.strip() == "":
                result = _idempotent_handler(store, key or "", {"title": "test"})
                assert result is None
            else:
                store.set(key, {"payload": {"title": "test"}, "response": {"ok": True}})
                result = _idempotent_handler(store, key, {"title": "test"})
                assert result == {"ok": True}


# ── Endpoint-level tests ───────────────────────────────────────────────────────

class TestIdempotencyAtEndpoints:
    @pytest.fixture
    def app_with_endpoint(self):
        app = FastAPI()
        store = _IdempotencyStore()

        @app.post("/api/v1/documents/upload")
        async def document_upload(request: dict):
            key = request.get("idempotency_key", "")
            if not key:
                return {"document_id": "doc-upload-new"}
            existing = store.get(key)
            if existing:
                if existing["payload"] != request:
                    from fastapi import HTTPException as H
                    raise H(422, detail="Payload mismatch")
                return existing["response"]
            result = {"document_id": "doc-upload-123"}
            store.set(key, {"payload": request, "response": result})
            return result

        @app.post("/api/v1/generator/sessions")
        async def generator_session(request: dict):
            key = request.get("idempotency_key", "")
            if not key:
                return {"session_id": "gen-session-new"}
            existing = store.get(key)
            if existing:
                return existing["response"]
            result = {"session_id": "gen-session-456"}
            store.set(key, {"payload": request, "response": result})
            return result

        @app.post("/api/v1/synthesis/sessions")
        async def synthesis_session(request: dict):
            key = request.get("idempotency_key", "")
            if not key:
                return {"session_id": "synth-session-new"}
            existing = store.get(key)
            if existing:
                return existing["response"]
            result = {"session_id": "synth-session-789"}
            store.set(key, {"payload": request, "response": result})
            return result

        app.state.store = store
        return app

    def test_document_upload_idempotency(self, app_with_endpoint):
        client = TestClient(app_with_endpoint)
        payload = {"file": "manuscript.pdf", "idempotency_key": "upload-1"}
        resp1 = client.post("/api/v1/documents/upload", json=payload)
        assert resp1.status_code == 200
        resp2 = client.post("/api/v1/documents/upload", json=payload)
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    def test_generator_session_idempotency(self, app_with_endpoint):
        client = TestClient(app_with_endpoint)
        payload = {"topic": "AI", "idempotency_key": "gen-1"}
        resp1 = client.post("/api/v1/generator/sessions", json=payload)
        assert resp1.status_code == 200
        resp2 = client.post("/api/v1/generator/sessions", json=payload)
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    def test_synthesis_session_idempotency(self, app_with_endpoint):
        client = TestClient(app_with_endpoint)
        payload = {"documents": ["doc-1"], "idempotency_key": "synth-1"}
        resp1 = client.post("/api/v1/synthesis/sessions", json=payload)
        assert resp1.status_code == 200
        resp2 = client.post("/api/v1/synthesis/sessions", json=payload)
        assert resp2.status_code == 200
        assert resp1.json() == resp2.json()

    def test_idempotency_key_logging_middleware(self):
        """Verify that RequestIdMiddleware logs idempotency keys on matching paths."""
        from app.middleware.request_id import RequestIdMiddleware, _should_log_idempotency
        assert _should_log_idempotency("/api/v1/documents/upload") is True
        assert _should_log_idempotency("/api/v1/generator/sessions") is True
        assert _should_log_idempotency("/api/v1/synthesis/sessions") is True
        assert _should_log_idempotency("/api/v1/documents") is False
