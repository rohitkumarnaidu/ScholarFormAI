# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Supabase Client - Server-Side DB Layer.

Provides a singleton supabase-py client using the SERVICE ROLE KEY for
all server-side database operations. This bypasses Row Level Security (RLS)
which is correct for backend operations that have already verified auth via JWT.

Design decisions:
- Uses SUPABASE_SERVICE_ROLE_KEY (not anon key) for server-side writes.
- Falls back gracefully: if credentials are missing, client is None and
  get_supabase_db() raises HTTP 503 instead of crashing the server.
- Keeps SQLAlchemy session layer for schema reference and future migrations.
"""

import logging
import warnings

from app.config.settings import settings

logger = logging.getLogger(__name__)

_SUPABASE_WARNING_FILTERS = (
    ".*enablePackrat.*",
    ".*escChar.*",
    ".*unquoteResults.*",
    "Using `@model_validator` with mode='after' on a classmethod is deprecated.*",
    "The 'timeout' parameter is deprecated. Please configure it in the http client instead.*",
    "The 'verify' parameter is deprecated. Please configure it in the http client instead.*",
)

# Apply narrow global suppression for known third-party deprecation noise.
for _pattern in _SUPABASE_WARNING_FILTERS:
    warnings.filterwarnings("ignore", message=_pattern, category=DeprecationWarning)

try:
    with warnings.catch_warnings():
        for pattern in _SUPABASE_WARNING_FILTERS:
            warnings.filterwarnings("ignore", message=pattern, category=DeprecationWarning)
        from supabase import create_client, Client
except Exception:  # pragma: no cover - optional dependency in some test envs
    create_client = None
    Client = object

# Singleton state
_supabase_client = None
_client_initialized = False


def _init_client():
    """
    Initialize the supabase-py client.
    Returns None (instead of raising) if credentials are missing.
    """
    global _supabase_client

    url = settings.SUPABASE_URL
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    if not url or not key:
        logger.warning(
            "[WARN] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set. "
            "DB-dependent endpoints will return 503 until credentials are configured."
        )
        return None

    try:
        if create_client is None:
            logger.error("[ERROR] Supabase client library is not available.")
            return None

        # Supabase internals currently trigger third-party deprecation warnings
        # (pyiceberg/postgrest). Keep logs clean until upstream packages update.
        with warnings.catch_warnings():
            for pattern in _SUPABASE_WARNING_FILTERS:
                warnings.filterwarnings("ignore", message=pattern, category=DeprecationWarning)
            _supabase_client = create_client(url, key)

        logger.info("[OK] Supabase DB client (service role) initialized successfully.")
        return _supabase_client
    except Exception as exc:
        logger.error("[ERROR] Failed to initialize Supabase DB client: %s", exc)
        return None


def get_supabase_client(refresh: bool = False):
    """
    Return the singleton Supabase client.

    Args:
        refresh: Force re-initialization (mainly for tests/recovery).

    Returns:
        The supabase client or None when unavailable/unconfigured.
    """
    global _supabase_client, _client_initialized

    if refresh:
        _client_initialized = False

    if not _client_initialized:
        _supabase_client = _init_client()
        _client_initialized = True

    return _supabase_client


def get_supabase_db():
    """
    FastAPI dependency that returns the Supabase client.
    Raises HTTP 503 if the client is not configured.
    """
    from fastapi import HTTPException, status

    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Database is not configured. "
                "Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            ),
        )
    return client


def check_supabase_health() -> dict:
    """
    Returns a dict describing current Supabase DB connectivity status.
    Used by the /health endpoint.
    """
    client = get_supabase_client()
    if client is None:
        return {
            "status": "unconfigured",
            "detail": "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set",
        }

    try:
        # Lightweight ping: select 1 row from profiles (limit 1)
        client.table("profiles").select("id").limit(1).execute()
        return {"status": "healthy"}
    except Exception as exc:
        return {"status": "unhealthy", "detail": str(exc)}
