# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import Request

from app.db.supabase_client import get_supabase_client
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditLogService:
    _audit_table_available: Optional[bool] = None
    _audit_table_warning_logged: bool = False

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _extract_resource(path: str) -> Tuple[str, Optional[str]]:
        segments = [segment for segment in (path or "").strip("/").split("/") if segment]
        while segments and segments[0] in {"api", "v1"}:
            segments.pop(0)

        resource_type = segments[0] if segments else "root"
        resource_id = segments[1] if len(segments) > 1 else None
        return resource_type, resource_id

    @staticmethod
    def _extract_user_id_from_auth_header(authorization_header: Optional[str]) -> Optional[str]:
        if not authorization_header:
            return None

        header = authorization_header.strip()
        if not header.lower().startswith("bearer "):
            return None

        token = header[7:].strip()
        if not token:
            return None

        try:
            payload = AuthService.decode_token(token)
            user_id = AuthService.get_user_id_from_payload(payload)
            return str(user_id) if user_id else None
        except Exception:
            return None

    async def log(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        ip_address: Optional[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._audit_table_available is False:
            return

        sb = get_supabase_client()
        if sb is None:
            logger.warning("Audit log skipped: Supabase client unavailable.")
            return

        event_timestamp = self._utc_now_iso()
        details_payload = dict(details or {})
        details_payload.setdefault("timestamp", event_timestamp)

        payload = {
            "user_id": str(user_id) if user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "ip_address": ip_address,
            "details": details_payload,
            "created_at": event_timestamp,
        }

        def run_insert():
            client = get_supabase_client()
            if client is None:
                raise RuntimeError("Supabase client not available.")
            return client.table("audit_log").insert(payload).execute()

        try:
            await asyncio.to_thread(run_insert)
            self._audit_table_available = True
        except Exception as exc:
            error_text = str(exc)
            missing_audit_table = (
                "audit_log" in error_text
                and "Could not find the table" in error_text
            )
            if missing_audit_table:
                self._audit_table_available = False
                if not self._audit_table_warning_logged:
                    logger.warning(
                        "Supabase table 'audit_log' not found; audit logging disabled until migration is applied."
                    )
                    self._audit_table_warning_logged = True
                return
            logger.warning("Audit log insert failed: %s", exc)

    async def log_http_write(
        self,
        request: Request,
        *,
        status_code: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        method = (request.method or "").upper()
        if method not in WRITE_METHODS:
            return

        resource_type, resource_id = self._extract_resource(request.url.path)
        user_id = self._extract_user_id_from_auth_header(request.headers.get("authorization"))
        ip_address = request.client.host if request.client else None

        metadata = {
            "method": method,
            "path": request.url.path,
            "status_code": int(status_code),
            "query": request.url.query or "",
            "request_id": request.headers.get("x-request-id"),
            "source": "write_middleware",
        }
        if details:
            metadata.update(details)

        await self.log(
            user_id=user_id,
            action=f"{method.lower()}_{resource_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=metadata,
        )


audit_log_service = AuditLogService()
