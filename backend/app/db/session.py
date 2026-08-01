# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Database Session Management.

Provides a SQLAlchemy engine and session factory for the application.

Design decisions:
- If SUPABASE_DB_URL is missing, the engine is set to None and the app
  starts in "degraded mode" — DB endpoints return 503, but the server
  does NOT crash. This matches the startup behaviour in app/main.py.
- Connection pool is tuned for a typical cloud-hosted Postgres (Supabase):
    pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800
- pool_pre_ping=True detects stale connections before use (prevents
  "SSL connection has been closed unexpectedly" errors after idle periods).
"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ── Engine factory ─────────────────────────────────────────────────────────────


def _create_engine_safe() -> Engine | None:
    """
    Create the SQLAlchemy engine.

    Returns None (instead of raising) when SUPABASE_DB_URL is not configured,
    allowing the server to start in degraded mode.
    """
    db_url = settings.SUPABASE_DB_URL
    if not db_url:
        logger.warning(
            " ️  SUPABASE_DB_URL is not set. Database-dependent endpoints will return 503 until it is configured."
        )
        return None

    try:
        engine = create_engine(
            db_url,
            # Connection pool tuning for cloud Postgres (Supabase)
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,  # Recycle connections after 30 min (avoids stale SSL)
            pool_pre_ping=True,  # Verify connection health before use
            echo=False,  # Set to True for SQL query debugging
        )
        logger.info("✅ Database engine created successfully.")
        return engine
    except Exception as exc:
        logger.error(
            "❌ Failed to create database engine: %s. DB endpoints will be unavailable.",
            exc,
        )
        return None


engine: Engine | None = _create_engine_safe()

# SessionLocal is None when engine is None (degraded mode)
SessionLocal: sessionmaker | None = (
    sessionmaker(autocommit=False, autoflush=False, bind=engine) if engine is not None else None
)


# ── FastAPI dependency ─────────────────────────────────────────────────────────


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session.

    - Automatically closes the session after each request.
    - Returns HTTP 503 (via HTTPException) when the DB is unconfigured.
    - Rolls back on unhandled SQLAlchemy errors to prevent connection leaks.

    Usage:
        @router.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    from fastapi import HTTPException, status  # local import avoids circular deps

    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Please set SUPABASE_DB_URL.",
        )

    db: Session = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        logger.error("Database error during request: %s", exc)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred. Please try again.",
        ) from exc
    finally:
        db.close()


# ── Health-check helper ────────────────────────────────────────────────────────


def check_db_health() -> dict:
    """
    Returns a dict describing the current database connectivity status.
    Used by the /health endpoint.
    """
    if engine is None:
        return {"status": "unconfigured", "detail": "SUPABASE_DB_URL not set"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except OperationalError as exc:
        return {"status": "unhealthy", "detail": str(exc)}
