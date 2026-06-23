# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.user import User
from app.utils.dependencies import get_current_user


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_user():
    user = User(id="user-123", email="user@example.com", role="authenticated")
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


def test_sse_stream_connection(client, authenticated_user):
    async def fake_event_generator(job_id, request):
        yield {"event": "connected", "data": '{"message":"ok"}'}

    with patch("app.routers.v1.stream.event_generator", fake_event_generator):
        response = client.get("/api/v1/stream/job-123")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "event: connected" in response.text


@pytest.mark.asyncio
async def test_emit_event_schedules_pubsub_publish():
    from app.routers.v1 import stream as stream_router

    with patch.object(stream_router._pubsub, "publish", new_callable=AsyncMock) as mock_publish:
        stream_router.emit_event("job-1", "STATUS", {"ok": True})
        await asyncio.sleep(0)

    mock_publish.assert_awaited_once()
    channel, event = mock_publish.await_args.args
    assert channel == "job:job-1"
    assert event["event_type"] == "STATUS"
    assert event["payload"]["ok"] is True
