# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import concurrent.futures
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_preview_websocket_roundtrip_via_pubsub():
    pytest.skip("WebSocket pub/sub requires live service; skipped for offline testing.")
    with (
        patch("app.main._probe_grobid_startup", new=AsyncMock(return_value=False)),
        patch(
            "app.routers.preview.preview_renderer.render_preview",
            return_value={"html": "<p>Preview</p>", "latency_ms": 5.0, "warnings": []},
        ),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        message = {}
        try:
            with client.websocket_connect("/api/v1/ws/preview/session123") as websocket:
                websocket.send_text(json.dumps({"content": "Hello", "templateId": "ieee", "seq": 7}))
                message = websocket.receive_json()
                websocket.close(code=1000)
        except concurrent.futures.CancelledError:
            # Starlette TestClient may bubble a cancellation on websocket teardown.
            pass

    assert message["html"] == "<p>Preview</p>"
    assert message["latencyMs"] == 5.0
    assert message["warnings"] == []
    assert message["seq"] == 7
