# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest
from starlette.requests import Request
from fastapi import HTTPException

from app.routers.v1._helpers import run_enveloped


def _request(path: str) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_run_enveloped_records_persona_kpis_success(monkeypatch):
    from app.middleware.prometheus_metrics import MetricsManager

    events = []
    latencies = []

    monkeypatch.setattr(
        MetricsManager,
        "record_persona_event",
        lambda persona, event, outcome: events.append((persona, event, outcome)),
    )
    monkeypatch.setattr(
        MetricsManager,
        "record_persona_latency",
        lambda persona, operation, duration_seconds: latencies.append((persona, operation, duration_seconds)),
    )

    async def operation():
        return {"ok": True}

    response = await run_enveloped(
        _request("/api/v1/generator/sessions"),
        operation,
        operation_name="generation session create",
    )

    assert response.status_code == 200
    assert events and events[0][0] == "authoring"
    assert events[0][2] == "success"
    assert latencies and latencies[0][2] >= 0


@pytest.mark.asyncio
async def test_run_enveloped_records_persona_kpis_error(monkeypatch):
    from app.middleware.prometheus_metrics import MetricsManager

    events = []
    latencies = []

    monkeypatch.setattr(
        MetricsManager,
        "record_persona_event",
        lambda persona, event, outcome: events.append((persona, event, outcome)),
    )
    monkeypatch.setattr(
        MetricsManager,
        "record_persona_latency",
        lambda persona, operation, duration_seconds: latencies.append((persona, operation, duration_seconds)),
    )

    async def operation():
        raise HTTPException(status_code=422, detail="bad request")

    response = await run_enveloped(
        _request("/api/v1/documents/upload"),
        operation,
        operation_name="document upload",
    )

    assert response.status_code == 422
    assert events and events[0][0] == "formatter"
    assert events[0][2] == "error"
    assert latencies and latencies[0][2] >= 0
