# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import pytest


class TestRetryWithBackoff:
    def test_sync_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        call_count = [0]
        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        def func():
            call_count[0] += 1
            return "ok"
        assert func() == "ok"
        assert call_count[0] == 1

    def test_sync_retry_and_succeed(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        call_count = [0]
        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("not yet")
            return "ok"
        assert func() == "ok"
        assert call_count[0] == 3

    def test_sync_fail_permanently(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        def func():
            raise ValueError("always fail")
        with pytest.raises(ValueError):
            func()

    def test_base_delay_migration(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        @retry_with_backoff(max_retries=1, base_delay=0.5)
        def func():
            return "ok"
        assert func() == "ok"

    def test_execute_with_retry_success(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        def func(x):
            return x * 2
        result = execute_with_retry(func, 21, max_retries=2, backoff_factor=0.01)
        assert result == 42

    def test_execute_with_retry_fail(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        def func():
            raise ValueError("nope")
        with pytest.raises(ValueError):
            execute_with_retry(func, max_retries=1, backoff_factor=0.01)

    @pytest.mark.asyncio
    async def test_async_success(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        call_count = [0]
        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        async def func():
            call_count[0] += 1
            return "async_ok"
        result = await func()
        assert result == "async_ok"

    @pytest.mark.asyncio
    async def test_async_retry_and_succeed(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        call_count = [0]
        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        async def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("not yet")
            return "ok"
        result = await func()
        assert result == "ok"
        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_async_fail_permanently(self):
        from app.pipeline.safety.retry_guard import retry_with_backoff
        @retry_with_backoff(max_retries=1, backoff_factor=0.01)
        async def func():
            raise ValueError("always fail")
        with pytest.raises(ValueError):
            await func()

    def test_retry_guard_alias(self):
        from app.pipeline.safety.retry_guard import retry_guard, retry_with_backoff
        assert retry_guard is retry_with_backoff

    def test_execute_with_retry_no_args(self):
        from app.pipeline.safety.retry_guard import execute_with_retry
        def fn():
            return 99
        assert execute_with_retry(fn) == 99
