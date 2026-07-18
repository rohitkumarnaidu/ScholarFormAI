# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.suggestion_service import suggestion_service
from app.utils.dependencies import get_current_user
from app.utils.logging_context import bind_request_context
from app.schemas.user import User

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


class GenerateSuggestionRequest(BaseModel):
    document_id: str
    block: Dict[str, Any]
    suggestion_type: str
    session_id: Optional[str] = None


@router.post("/generate", status_code=201)
async def generate_suggestion(
    request: Request,
    body: GenerateSuggestionRequest,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        suggestion = await suggestion_service.generate_suggestion(
            document_id=body.document_id,
            block=body.block,
            suggestion_type=body.suggestion_type,
            user_id=str(current_user.id),
            session_id=body.session_id,
        )
        if suggestion is None:
            raise HTTPException(
                status_code=400,
                detail="Failed to generate suggestion. Check your text and suggestion type.",
            )
        return suggestion

    return await run_enveloped(
        request,
        operation,
        success_status_code=201,
        code_map={
            400: "SUGGESTION_GENERATION_FAILED",
            401: "UNAUTHORIZED",
            422: "INVALID_SUGGESTION_REQUEST",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestion generate",
    )


@router.get("/document/{document_id}")
async def get_document_suggestions(
    request: Request,
    document_id: str,
    status: Optional[str] = Query(None, pattern="^(pending|accepted|rejected|dismissed)?$"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        suggestions = await suggestion_service.get_suggestions(
            document_id=document_id,
            status=status,
            limit=limit,
        )
        return {
            "suggestions": suggestions,
            "total": len(suggestions),
            "document_id": document_id,
        }

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestions list",
    )


@router.post("/{suggestion_id}/accept")
async def accept_suggestion(
    request: Request,
    suggestion_id: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        result = await suggestion_service.accept_suggestion(suggestion_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        return result

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            404: "SUGGESTION_NOT_FOUND",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestion accept",
    )


@router.post("/{suggestion_id}/reject")
async def reject_suggestion(
    request: Request,
    suggestion_id: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        result = await suggestion_service.reject_suggestion(suggestion_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        return result

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            404: "SUGGESTION_NOT_FOUND",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestion reject",
    )


@router.post("/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    request: Request,
    suggestion_id: str,
    current_user: User = Depends(get_current_user),
):
    async def operation():
        result = await suggestion_service.dismiss_suggestion(suggestion_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        return result

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            404: "SUGGESTION_NOT_FOUND",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestion dismiss",
    )


@router.post("/{suggestion_id}/apply")
async def apply_suggestion(
    request: Request,
    suggestion_id: str,
    document_id: str = Query(..., description="Document ID to apply the suggestion to"),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        result = await suggestion_service.apply_suggestion(
            suggestion_id=suggestion_id,
            document_id=document_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Suggestion not found or already applied")
        return result

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            404: "SUGGESTION_NOT_FOUND",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestion apply",
    )


@router.get("/history")
async def get_suggestion_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    async def operation():
        history = await suggestion_service.get_suggestion_history(
            user_id=str(current_user.id),
            limit=limit,
        )
        return {
            "suggestions": history,
            "total": len(history),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            503: "DATABASE_UNAVAILABLE",
        },
        logger=logger,
        operation_name="suggestion history",
    )
