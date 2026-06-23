# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi.responses import JSONResponse

from app.middleware.tier_rate_limit import TierRateLimitMiddleware


@pytest.mark.asyncio
async def test_guest_daily_limit_blocks():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/api/v1/documents/upload"
    request.headers = {}
    request.client.host = "1.2.3.4"

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    first = await middleware.dispatch(request, call_next)
    second = await middleware.dispatch(request, call_next)

    assert first.status_code == 200
    assert second.status_code == 429


@pytest.mark.asyncio
async def test_tier_limit_skips_health():
    middleware = TierRateLimitMiddleware(MagicMock(), guest_daily_limit=1)
    middleware._redis = None

    request = MagicMock()
    request.method = "POST"
    request.url = MagicMock()
    request.url.path = "/health"
    request.headers = {}
    request.client.host = "1.2.3.4"

    call_next = AsyncMock(return_value=JSONResponse({"ok": True}))

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
