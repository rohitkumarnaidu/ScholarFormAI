# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.config.settings import settings

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None

logger = logging.getLogger(__name__)


class RedisPubSub:
    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis_enabled = bool(settings.REDIS_ENABLED)
        self._redis_warning_logged = False
        self._force_fallback = False
        self._lock = asyncio.Lock()
        self._redis_by_loop: dict[int, Any] = {}
        self._fallback_channels: dict[str, set[asyncio.Queue]] = {}

    async def _get_redis(self):
        if not self._redis_enabled or self._force_fallback or aioredis is None:
            return None
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        client = self._redis_by_loop.get(loop_id)
        if client is not None:
            return client
        async with self._lock:
            client = self._redis_by_loop.get(loop_id)
            if client is not None:
                return client
            try:
                client = aioredis.from_url(self._redis_url, decode_responses=True)
                await client.ping()
                self._redis_by_loop[loop_id] = client
                return client
            except Exception as exc:
                if not self._redis_warning_logged:
                    logger.warning(
                        "Redis pubsub unavailable (%s). Falling back to in-memory queues.",
                        exc,
                    )
                    self._redis_warning_logged = True
                self._force_fallback = True
                return None

    async def publish(self, channel: str, event: dict) -> None:
        if not channel:
            return
        redis_client = await self._get_redis()
        if redis_client is not None:
            try:
                await redis_client.publish(channel, json.dumps(event))
                return
            except Exception as exc:
                if not self._redis_warning_logged:
                    logger.warning(
                        "Redis publish failed (%s). Falling back to in-memory queues.",
                        exc,
                    )
                    self._redis_warning_logged = True
                self._force_fallback = True

        queues = list(self._fallback_channels.get(channel, set()))
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue

    async def subscribe(self, channel: str) -> AsyncGenerator[dict, None]:
        if not channel:
            return
        redis_client = await self._get_redis()
        if redis_client is not None:
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel)
            try:
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    data = message.get("data")
                    if data is None:
                        continue
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode("utf-8", errors="ignore")
                    if isinstance(data, str):
                        try:
                            payload = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                    elif isinstance(data, dict):
                        payload = data
                    else:
                        continue
                    yield payload
            finally:
                try:
                    await pubsub.unsubscribe(channel)
                finally:
                    close_coro = getattr(pubsub, "aclose", None)
                    if callable(close_coro):
                        await close_coro()
                    else:
                        await pubsub.close()
            return

        queue: asyncio.Queue = asyncio.Queue()
        self._fallback_channels.setdefault(channel, set()).add(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self._fallback_channels.get(channel, set()).discard(queue)
