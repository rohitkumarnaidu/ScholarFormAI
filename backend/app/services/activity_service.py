# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.db.supabase_client import get_supabase_client
from app.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)

ACTIVITY_TYPES = frozenset(
    {
        "upload",
        "format",
        "download",
        "edit",
        "export",
        "template_change",
        "batch_upload",
    }
)


class ActivityService:
    _table_available: bool | None = None
    _table_warning_logged: bool = False

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _compute_period_start(period: str) -> datetime | None:
        now = datetime.now(UTC)
        if period == "7d":
            return now - timedelta(days=7)
        if period == "30d":
            return now - timedelta(days=30)
        if period == "90d":
            return now - timedelta(days=90)
        if period == "all":
            return None
        return now - timedelta(days=7)

    @classmethod
    async def record_activity(
        cls,
        user_id: str,
        activity_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if cls._table_available is False:
            return

        if activity_type not in ACTIVITY_TYPES:
            logger.warning("Unknown activity type: %s", activity_type)
            return

        sb = get_supabase_client()
        if sb is None:
            logger.warning("Activity record skipped: Supabase client unavailable.")
            return

        payload: dict[str, Any] = {
            "user_id": str(user_id),
            "activity_type": activity_type,
            "metadata": metadata or {},
            "created_at": cls._utc_now_iso(),
        }

        def run_insert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("user_activity").insert(payload).execute()

        try:
            await asyncio.to_thread(run_insert)
            cls._table_available = True
        except Exception as exc:
            error_text = str(exc)
            missing_table = "user_activity" in error_text and "Could not find the table" in error_text
            if missing_table:
                cls._table_available = False
                if not cls._table_warning_logged:
                    logger.warning(
                        "Supabase table 'user_activity' not found; "
                        "activity logging disabled until migration is applied."
                    )
                    cls._table_warning_logged = True
                return
            logger.warning("Activity record insert failed: %s", exc)

    @classmethod
    async def get_recent_activities(
        cls,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("user_activity")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_query)
            return result.data or []
        except Exception as exc:
            error_text = str(exc)
            if "Could not find the table" in error_text:
                return []
            logger.error("get_recent_activities failed: %s", exc)
            raise DatabaseUnavailableError(f"Failed to get activities: {exc}") from exc

    @classmethod
    async def get_activity_summary(
        cls,
        user_id: str,
        period: str = "7d",
    ) -> dict[str, Any]:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        period_start = cls._compute_period_start(period)

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            query = client.table("user_activity").select("*").eq("user_id", str(user_id))
            if period_start:
                query = query.gte("created_at", period_start.isoformat())
            return query.execute()

        try:
            result = await asyncio.to_thread(run_query)
            rows = result.data or []

            type_counts: dict[str, int] = {}
            for row in rows:
                atype = row.get("activity_type", "unknown")
                type_counts[atype] = type_counts.get(atype, 0) + 1

            return {
                "total_activities": len(rows),
                "period": period,
                "activity_breakdown": type_counts,
                "most_frequent": max(type_counts, key=type_counts.get) if type_counts else None,
            }
        except Exception as exc:
            error_text = str(exc)
            if "Could not find the table" in error_text:
                return {"total_activities": 0, "period": period, "activity_breakdown": {}}
            logger.error("get_activity_summary failed: %s", exc)
            raise DatabaseUnavailableError(f"Failed to get activity summary: {exc}") from exc


activity_service = ActivityService()
