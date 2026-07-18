# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.supabase_client import get_supabase_client
from app.exceptions import DatabaseUnavailableError

logger = logging.getLogger(__name__)

SUGGESTION_TYPES = frozenset({"style", "grammar", "structure", "citation", "clarity"})
SUGGESTION_STATUSES = frozenset({"pending", "accepted", "rejected", "dismissed"})

_SUGGESTION_PROMPTS: Dict[str, str] = {
    "style": (
        "You are an academic writing style expert. Suggest improvements for the following "
        "text to make it more consistent with formal academic style. Focus on tone, "
        "formality, and adherence to standard academic conventions. "
        "Return only the improved text without explanation."
    ),
    "grammar": (
        "You are a grammar and language expert. Correct any grammar, punctuation, "
        "spelling, or syntax issues in the following text while preserving the original "
        "meaning and academic tone. Return only the corrected text without explanation."
    ),
    "structure": (
        "You are an academic document structure expert. Suggest structural improvements "
        "for the following text to improve logical flow, paragraph organization, and "
        "section coherence. Return only the improved text without explanation."
    ),
    "citation": (
        "You are a citation and reference expert. Identify any citation issues in the "
        "following text and suggest corrections following standard academic citation "
        "formats. Return only the corrected text without explanation."
    ),
    "clarity": (
        "You are a clarity and readability expert. Suggest improvements to make the "
        "following text clearer, more concise, and easier to read while preserving "
        "academic rigor. Return only the improved text without explanation."
    ),
}


class SuggestionService:
    _table_available: Optional[bool] = None
    _table_warning_logged: bool = False

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _build_suggestion_prompt(original_text: str, suggestion_type: str) -> List[Dict[str, str]]:
        system_prompt = _SUGGESTION_PROMPTS.get(
            suggestion_type,
            "You are an academic writing assistant. Suggest improvements for the following text.",
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Original text:\n\n{original_text}"},
        ]

    @classmethod
    async def _call_llm_for_suggestion(
        cls,
        original_text: str,
        suggestion_type: str,
    ) -> Optional[str]:
        messages = cls._build_suggestion_prompt(original_text, suggestion_type)
        try:
            from app.services.llm_service import generate_with_fallback

            result = generate_with_fallback(
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            text = result.get("text", "").strip()
            return text if text else None
        except Exception as exc:
            logger.warning("LLM suggestion generation failed for type '%s': %s", suggestion_type, exc)
            return None

    @classmethod
    async def generate_suggestion(
        cls,
        document_id: str,
        block: Dict[str, Any],
        suggestion_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if suggestion_type not in SUGGESTION_TYPES:
            logger.warning("Unknown suggestion type: %s", suggestion_type)
            return None

        original_text = block.get("text", "")
        if not original_text or not original_text.strip():
            return None

        suggested_text = await cls._call_llm_for_suggestion(original_text, suggestion_type)
        if not suggested_text:
            suggested_text = original_text

        context = {
            "block_id": block.get("id"),
            "block_type": block.get("type"),
            "section": block.get("section"),
            "heading": block.get("heading"),
            "paragraph_index": block.get("index"),
        }

        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        payload: Dict[str, Any] = {
            "user_id": str(user_id) if user_id else None,
            "document_id": str(document_id),
            "session_id": session_id,
            "original_text": original_text,
            "suggested_text": suggested_text,
            "suggestion_type": suggestion_type,
            "score": 0.0,
            "status": "pending",
            "context": context,
            "created_at": cls._utc_now_iso(),
        }

        def run_insert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("suggestions").insert(payload).execute()

        try:
            result = await asyncio.to_thread(run_insert)
            cls._table_available = True
            return result.data[0] if result.data else None
        except Exception as exc:
            error_text = str(exc)
            if "Could not find the table" in error_text:
                cls._table_available = False
                if not cls._table_warning_logged:
                    logger.warning(
                        "Supabase table 'suggestions' not found; "
                        "suggestion creation disabled until migration is applied."
                    )
                    cls._table_warning_logged = True
                return None
            logger.error("generate_suggestion insert failed: %s", exc)
            raise DatabaseUnavailableError(f"Failed to create suggestion: {exc}") from exc

    @classmethod
    async def get_suggestions(
        cls,
        document_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            query = (
                client.table("suggestions")
                .select("*")
                .eq("document_id", str(document_id))
                .order("created_at", desc=True)
                .limit(limit)
            )
            if status:
                query = query.eq("status", status)
            return query.execute()

        try:
            result = await asyncio.to_thread(run_query)
            return result.data or []
        except Exception as exc:
            error_text = str(exc)
            if "Could not find the table" in error_text:
                return []
            logger.error("get_suggestions failed: %s", exc)
            raise DatabaseUnavailableError(f"Failed to get suggestions: {exc}") from exc

    @classmethod
    async def _update_suggestion_status(
        cls,
        suggestion_id: str,
        status: str,
    ) -> Optional[Dict[str, Any]]:
        if status not in SUGGESTION_STATUSES:
            return None

        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        updates: Dict[str, Any] = {
            "status": status,
            "updated_at": cls._utc_now_iso(),
        }
        if status == "accepted":
            updates["accepted_at"] = cls._utc_now_iso()

        def run_update():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("suggestions")
                .update(updates)
                .eq("id", str(suggestion_id))
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_update)
            return result.data[0] if result.data else None
        except Exception as exc:
            logger.error("update_suggestion_status(%s) failed: %s", suggestion_id, exc)
            raise DatabaseUnavailableError(f"Failed to update suggestion: {exc}") from exc

    @classmethod
    async def accept_suggestion(cls, suggestion_id: str) -> Optional[Dict[str, Any]]:
        return await cls._update_suggestion_status(suggestion_id, "accepted")

    @classmethod
    async def reject_suggestion(cls, suggestion_id: str) -> Optional[Dict[str, Any]]:
        return await cls._update_suggestion_status(suggestion_id, "rejected")

    @classmethod
    async def dismiss_suggestion(cls, suggestion_id: str) -> Optional[Dict[str, Any]]:
        return await cls._update_suggestion_status(suggestion_id, "dismissed")

    @classmethod
    async def get_suggestion_history(
        cls,
        user_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_query():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("suggestions")
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
            logger.error("get_suggestion_history failed: %s", exc)
            raise DatabaseUnavailableError(f"Failed to get suggestion history: {exc}") from exc

    @classmethod
    async def apply_suggestion(
        cls,
        suggestion_id: str,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        sb = get_supabase_client()
        if sb is None:
            raise DatabaseUnavailableError("Supabase client is not configured.")

        def run_fetch():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("suggestions")
                .select("*")
                .eq("id", str(suggestion_id))
                .eq("document_id", str(document_id))
                .maybe_single()
                .execute()
            )

        try:
            result = await asyncio.to_thread(run_fetch)
            suggestion = result.data if result else None
        except Exception as exc:
            logger.error("apply_suggestion fetch failed: %s", exc)
            raise DatabaseUnavailableError(f"Failed to fetch suggestion: {exc}") from exc

        if not suggestion:
            return None

        if suggestion.get("status") != "pending":
            return suggestion

        await cls._update_suggestion_status(suggestion_id, "accepted")

        doc_result = None

        def run_fetch_result():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return (
                client.table("document_results")
                .select("*")
                .eq("document_id", str(document_id))
                .maybe_single()
                .execute()
            )

        try:
            doc_res = await asyncio.to_thread(run_fetch_result)
            doc_result = doc_res.data if doc_res else None
        except Exception:
            logger.warning("Could not fetch document result for suggestion apply.")

        if doc_result:
            structured_data = doc_result.get("structured_data") or {}
            blocks = structured_data.get("blocks") or structured_data.get("sections", [])
            context = suggestion.get("context") or {}
            block_id = context.get("block_id")

            if block_id:
                updated = False
                for block in blocks:
                    if str(block.get("id")) == str(block_id):
                        block["text"] = suggestion["suggested_text"]
                        updated = True
                        break

                if updated:
                    def run_update_result():
                        client = get_supabase_client()
                        if client is None:
                            raise RuntimeError("Supabase client not available.")
                        return (
                            client.table("document_results")
                            .update({"structured_data": structured_data})
                            .eq("document_id", str(document_id))
                            .execute()
                        )

                    try:
                        await asyncio.to_thread(run_update_result)
                    except Exception as exc:
                        logger.warning("apply_suggestion document update failed: %s", exc)

        return await cls._update_suggestion_status(suggestion_id, "accepted")


suggestion_service = SuggestionService()
