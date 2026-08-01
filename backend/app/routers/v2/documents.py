# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.schemas.user import User
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_db():
    from app.db.supabase_client import get_supabase_client

    if get_supabase_client() is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )


def _to_document_list_item(doc: dict) -> dict:
    return {
        "id": str(doc.get("id")),
        "filename": doc.get("filename"),
        "template": doc.get("template"),
        "status": doc.get("status"),
        "progress": doc.get("progress", 0),
        "current_stage": doc.get("current_stage"),
        "error_message": doc.get("error_message"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


@router.get("")
async def list_documents(
    request: Request,
    cursor: str | None = Query(None, description="Base64-encoded cursor from previous page"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    order_by: str = Query("created_at", description="Column to order results by"),
    order_dir: str = Query("desc", description="Order direction: asc or desc"),
    status: str | None = Query(None, description="Filter by document status"),
    template: str | None = Query(None, description="Filter by template name"),
    current_user: User = Depends(get_current_user),
):
    _require_db()

    from app.db.supabase_client import get_supabase_client
    from app.utils.pagination import build_cursor_query, build_cursor_response

    sb = get_supabase_client()
    if sb is None:
        raise HTTPException(status_code=503, detail="Database not available")

    cursor_column = "created_at"
    params = SimpleNamespace(
        cursor=cursor,
        limit=limit,
        order_by=order_by,
        order_dir=order_dir,
    )

    query = sb.table("documents").select("*").eq("user_id", str(current_user.id))

    if status:
        query = query.eq("status", status.upper())
    if template:
        query = query.eq("template", template.upper())

    try:
        query = build_cursor_query(query, params, cursor_column=cursor_column)
    except HTTPException:
        raise

    try:
        result = await asyncio.to_thread(query.execute)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing documents (v2): %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    items = result.data if result.data else []
    page = build_cursor_response(items, params, cursor_column=cursor_column)

    mapped = [_to_document_list_item(d) for d in page["items"]]

    response_payload = {
        "items": mapped,
        "next_cursor": page["next_cursor"],
        "has_more": page["has_more"],
        "total": None,
    }

    return JSONResponse(
        content=response_payload,
        headers={
            "X-API-Version": "2",
        },
    )
