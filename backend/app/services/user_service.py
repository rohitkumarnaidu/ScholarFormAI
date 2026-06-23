# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
User Service — Supabase DB Layer.

All database operations for the `profiles` table go through this service
using the supabase-py client.

The old SQLAlchemy ORM imports are kept as comments for reference.
The SQLAlchemy ORM model (app/models/user.py) is still the canonical
schema definition and is used by Alembic migrations.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional, Dict, Any

from postgrest import APIError

from app.db.supabase_client import get_supabase_client
from app.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)


class UserService:
    """
    Service layer for all user/profile-related DB operations.
    Uses supabase-py for all reads and writes.
    """

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user profile by ID.
        Returns None if not found.
        Raises DatabaseUnavailableError on database errors.

        Old ORM equivalent:
            db.query(UserModel).filter(UserModel.id == user_id).first()
        """
        sb = get_supabase_client()
        if sb is None:
            logger.error("get_user_by_id: Supabase client not available.")
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("profiles")
                .select("*")
                .eq("id", str(user_id))
                .maybe_single()
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_query)
            return result.data
        except APIError as e:
            logger.error("get_user_by_id(%s) failed: %s", user_id, e)
            raise DatabaseUnavailableError(f"Failed to get user: {e}") from e
        except Exception as e:
            logger.error("get_user_by_id(%s) failed: %s", user_id, e)
            raise DatabaseUnavailableError(f"Failed to get user: {e}") from e

    @staticmethod
    async def update_user_profile(
        user_id: str,
        email: str,
        full_name: str,
        institution: str,
        role: str = "authenticated",
    ) -> Optional[Dict[str, Any]]:
        """
        Upsert a user profile row (insert if new, update if exists).
        Returns the upserted row dict or None on error.
        Raises DatabaseUnavailableError on database errors.

        Old ORM equivalent:
            user = db.query(UserModel).filter(UserModel.id == user_id).first()
            if not user:
                user = UserModel(id=user_id, ...)
                db.add(user)
            else:
                user.email = email; ...
            db.commit(); db.refresh(user); return user
        """
        sb = get_supabase_client()
        if sb is None:
            logger.error("update_user_profile: Supabase client not available.")
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_upsert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            payload: Dict[str, Any] = {
                "id": str(user_id),
                "email": email,
                "full_name": full_name,
                "institution": institution,
                "role": role,
            }
            return (
                client.table("profiles")
                .upsert(payload, on_conflict="id")
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_upsert)
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error("update_user_profile(%s) failed: %s", user_id, e)
            raise DatabaseUnavailableError(f"Failed to update user profile: {e}") from e
        except Exception as e:
            logger.error("update_user_profile(%s) failed: %s", user_id, e)
            raise DatabaseUnavailableError(f"Failed to update user profile: {e}") from e

    @staticmethod
    async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user profile by email address.
        Returns None if not found.
        Raises DatabaseUnavailableError on database errors.
        """
        sb = get_supabase_client()
        if sb is None:
            logger.error("get_user_by_email: Supabase client not available.")
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("profiles")
                .select("*")
                .eq("email", email)
                .maybe_single()
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_query)
            return result.data
        except APIError as e:
            logger.error("get_user_by_email(%s) failed: %s", email, e)
            raise DatabaseUnavailableError(f"Failed to get user by email: {e}") from e
        except Exception as e:
            logger.error("get_user_by_email(%s) failed: %s", email, e)
            raise DatabaseUnavailableError(f"Failed to get user by email: {e}") from e
