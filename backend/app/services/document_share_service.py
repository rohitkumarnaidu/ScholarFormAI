# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Document share service — sharing and permission management.

Extracted from the fat `document_service.py`. Handles the
`document_shares` table: granting/revoking access, listing shared users,
and checking permissions (owner or shared).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

from app.db.supabase_client import get_supabase_client
from app.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)


class DocumentShareService:
    """Sharing + permission logic for documents."""

    async def share_document(
        self,
        document_id: str,
        shared_with_user_id: str,
        permission: str,
        shared_by_user_id: str,
    ) -> Dict[str, Any]:
        """Share a document with another user."""
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_share():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("document_shares")
                .upsert(
                    {
                        "document_id": document_id,
                        "shared_with_user_id": shared_with_user_id,
                        "permission": permission,
                        "shared_by_user_id": shared_by_user_id,
                    },
                    on_conflict="document_id,shared_with_user_id",
                )
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_share)
            return result.data[0] if result.data else {}
        except Exception as exc:
            logger.error("share_document(%s) failed: %s", document_id, exc)
            raise DatabaseUnavailableError(f"Failed to share document: {exc}") from exc

    async def get_shared_documents(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get documents shared with a user (joined with documents table)."""
        sb = get_supabase_client()
        if sb is None:
            return []

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("document_shares")
                .select(
                    "id, document_id, permission, shared_by_user_id, created_at, "
                    "documents!inner(id, filename, template, status, progress, "
                    "current_stage, created_at, updated_at)"
                )
                .eq("shared_with_user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_query)
            return result.data or []
        except Exception as exc:
            logger.warning("get_shared_documents failed: %s", exc)
            return []

    async def remove_sharing(self, document_id: str, shared_with_user_id: str) -> bool:
        """Remove sharing access from a user."""
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_delete():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("document_shares")
                .delete()
                .eq("document_id", document_id)
                .eq("shared_with_user_id", shared_with_user_id)
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_delete)
            return len(result.data or []) > 0
        except Exception as exc:
            logger.error("remove_sharing(%s, %s) failed: %s", document_id, shared_with_user_id, exc)
            raise DatabaseUnavailableError(f"Failed to remove sharing: {exc}") from exc

    async def check_document_access(self, document_id: str, user_id: str) -> bool:
        """Check if a user has access to a document (owner or shared)."""
        sb = get_supabase_client()
        if sb is None:
            return False

        def run_check():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            owner = (
                client.table("documents")
                .select("id")
                .eq("id", document_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if owner.data:
                return True
            share = (
                client.table("document_shares")
                .select("id")
                .eq("document_id", document_id)
                .eq("shared_with_user_id", user_id)
                .maybe_single()
                .execute()
            )
            return bool(share.data)

        try:
            return await asyncio.to_thread(run_check)
        except Exception as exc:
            logger.warning("check_document_access(%s) failed: %s", document_id, exc)
            return False

    # Convenience aliases to match the documented facade surface.

    async def unshare_document(self, document_id: str, user_id: str) -> bool:
        return await self.remove_sharing(document_id, user_id)

    async def get_shared_users(self, document_id: str) -> List[Dict[str, Any]]:
        sb = get_supabase_client()
        if sb is None:
            return []
        try:
            result = await asyncio.to_thread(
                lambda: (
                    get_supabase_client()
                    .table("document_shares")
                    .select("shared_with_user_id, permission, shared_by_user_id, created_at")
                    .eq("document_id", document_id)
                    .execute()
                )
            )
            return result.data or []
        except Exception as exc:
            logger.warning("get_shared_users(%s) failed: %s", document_id, exc)
            return []

    async def check_permission(self, document_id: str, user_id: str) -> bool:
        return await self.check_document_access(document_id, user_id)
