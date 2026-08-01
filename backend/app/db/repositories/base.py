from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC

from app.db.supabase_client import get_supabase_client
from app.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)

TRANSIENT_ERROR_MARKERS = (
    "remoteprotocolerror",
    "server disconnected",
    "connection reset",
    "connection aborted",
    "connection refused",
    "read timed out",
    "connect timeout",
    "timed out",
    "temporarily unavailable",
    "network is unreachable",
)


def is_transient_supabase_error(exc: Exception) -> bool:
    exc_name = type(exc).__name__.lower()
    if exc_name in {"remoteprotocolerror", "connecterror", "readtimeout", "writetimeout"}:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in TRANSIENT_ERROR_MARKERS)


async def execute_with_transient_retry(
    operation_name: str,
    operation,
    *,
    job_id: str | None = None,
    max_attempts: int = 3,
):
    from app.utils.logging_context import log_extra

    attempt = 0
    while True:
        try:
            return await asyncio.to_thread(operation)
        except Exception as exc:
            attempt += 1
            should_retry = is_transient_supabase_error(exc) and attempt < max_attempts
            if not should_retry:
                raise

            delay_seconds = 0.15 * (2 ** (attempt - 1))
            logger.warning(
                "%s transient Supabase error (attempt %s/%s): %s; retrying in %.2fs",
                operation_name,
                attempt,
                max_attempts,
                exc,
                delay_seconds,
                extra=log_extra(job_id=job_id),
            )
            get_supabase_client(refresh=True)
            await asyncio.sleep(delay_seconds)


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


class BaseRepository(ABC):
    TABLE_NAME: str

    @staticmethod
    def _get_client():
        client = get_supabase_client()
        if client is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")
        return client

    @staticmethod
    def _is_available() -> bool:
        return get_supabase_client() is not None

    def _table(self):
        return self._get_client().table(self.TABLE_NAME)
