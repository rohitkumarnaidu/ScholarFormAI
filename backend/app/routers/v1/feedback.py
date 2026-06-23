# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.db.supabase_client import get_supabase_client
from app.pipeline.agents.memory import AgentMemory
from app.utils.dependencies import get_current_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])
memory = AgentMemory()


class FeedbackRequest(BaseModel):
    document_id: str
    field: str
    original_value: Any
    corrected_value: Any
    comments: Optional[str] = None


@router.post("/", status_code=201)
async def submit_feedback(
    request: Request,
    feedback: FeedbackRequest,
    current_user=Depends(get_current_user),
):
    async def operation():
        try:
            memory.remember_correction(
                document_id=feedback.document_id,
                field=feedback.field,
                original_value=feedback.original_value,
                corrected_value=feedback.corrected_value,
            )

            try:
                sb = get_supabase_client()
                if sb:
                    payload = {
                        "document_id": feedback.document_id,
                        "user_id": str(current_user.id),
                        "field": feedback.field,
                        "original_value": str(feedback.original_value),
                        "corrected_value": str(feedback.corrected_value),
                        "comments": feedback.comments,
                    }

                    def run_insert():
                        client = get_supabase_client()
                        if client is None:
                            raise RuntimeError("Supabase client not available.")
                        return client.table("feedback").insert(payload).execute()

                    await asyncio.to_thread(run_insert)
            except Exception as db_err:
                logger.warning("Failed to persist feedback to Supabase: %s", db_err)

            return {"status": "success", "message": "Feedback recorded successfully"}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return await run_enveloped(
        request,
        operation,
        success_status_code=201,
        code_map={
            401: "UNAUTHORIZED",
            422: "INVALID_FEEDBACK_REQUEST",
        },
        logger=logger,
        operation_name="feedback submit",
    )


@router.get("/summary")
async def get_feedback_summary(
    request: Request,
    current_user=Depends(get_current_user),
):
    async def operation():
        try:
            summary = memory.get_memory_summary()
            return summary.get("corrections", {})
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return await run_enveloped(
        request,
        operation,
        code_map={401: "UNAUTHORIZED"},
        logger=logger,
        operation_name="feedback summary",
    )
