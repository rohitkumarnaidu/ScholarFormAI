# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.generator_session_service import GeneratorSessionService


def _build_table_mock(*, data):
    table = MagicMock()
    table.select.return_value = table
    table.eq.return_value = table
    table.order.return_value = table
    table.limit.return_value = table
    table.maybe_single.return_value = table
    table.insert.return_value = table
    table.update.return_value = table
    table.execute.return_value = SimpleNamespace(data=data)
    return table


@pytest.mark.asyncio
async def test_get_session_uses_cache_within_ttl(monkeypatch):
    service = GeneratorSessionService()
    monkeypatch.setattr(service, "_session_ttl_seconds", lambda: 5.0)

    sessions_table = _build_table_mock(data={"id": "session-1", "status": "processing"})
    supabase = MagicMock()
    supabase.table.side_effect = lambda name: sessions_table

    with patch("app.services.generator_session_service.get_supabase_client", return_value=supabase):
        first = await service.get_session("session-1")
        second = await service.get_session("session-1")

    assert first == second
    assert sessions_table.select.call_count == 1
    assert sessions_table.execute.call_count == 1


@pytest.mark.asyncio
async def test_get_session_cache_expires_after_ttl(monkeypatch):
    service = GeneratorSessionService()
    monkeypatch.setattr(service, "_session_ttl_seconds", lambda: 0.01)

    sessions_table = _build_table_mock(data={"id": "session-1", "status": "processing"})
    supabase = MagicMock()
    supabase.table.side_effect = lambda name: sessions_table

    with patch("app.services.generator_session_service.get_supabase_client", return_value=supabase):
        await service.get_session("session-1")
        await asyncio.sleep(0.02)
        await service.get_session("session-1")

    assert sessions_table.select.call_count == 2
    assert sessions_table.execute.call_count == 2


@pytest.mark.asyncio
async def test_add_message_invalidates_messages_cache(monkeypatch):
    service = GeneratorSessionService()
    monkeypatch.setattr(service, "_messages_ttl_seconds", lambda: 10.0)

    messages_table = _build_table_mock(
        data=[{"role": "assistant", "content": "hello", "created_at": "2026-01-01T00:00:00+00:00"}]
    )
    sessions_table = _build_table_mock(data={"id": "session-1"})
    supabase = MagicMock()

    def table_side_effect(name: str):
        if name == "generator_messages":
            return messages_table
        if name == "generator_sessions":
            return sessions_table
        return _build_table_mock(data=None)

    supabase.table.side_effect = table_side_effect

    with patch("app.services.generator_session_service.get_supabase_client", return_value=supabase):
        first = await service.get_messages("session-1", limit=25)
        second = await service.get_messages("session-1", limit=25)
        await service.add_message("session-1", role="user", content="rewrite this", token_count=0)
        third = await service.get_messages("session-1", limit=25)

    assert first == second == third
    assert messages_table.select.call_count == 2
