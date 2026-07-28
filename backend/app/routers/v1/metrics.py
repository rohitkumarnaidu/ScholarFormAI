# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

from app.db.supabase_client import get_supabase_client
from app.middleware.rbac import require_role
from app.services.ab_testing import get_ab_testing
from app.services.enhancement_manager import enhancement_manager
from app.services.model_metrics import get_model_metrics
from app.services.vllm_adoption import build_vllm_adoption_report
from app.utils.dependencies import get_optional_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


@router.get("")
async def get_metrics_summary(request: Request):
    """Metrics summary endpoint returning aggregated system metrics overview."""
    async def operation():
        model_metrics = get_model_metrics()
        ab_testing = get_ab_testing()
        summary = model_metrics.get_summary() if hasattr(model_metrics, "get_summary") else {}
        ab_summary = ab_testing.get_test_summary() if hasattr(ab_testing, "get_test_summary") else {}
        return {
            "status": "success",
            "model_metrics": summary,
            "ab_test_summary": ab_summary,
        }

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="metrics summary",
    )


@router.get("/db")
async def get_database_metrics(
    request: Request,
    admin_user=Depends(require_role("admin")),
):
    async def operation():
        try:
            sb = get_supabase_client()
            if sb:
                result = sb.table("documents").select("id", count="exact").limit(0).execute()
                metrics = {
                    "status": "healthy",
                    "backend": "supabase",
                    "document_count": result.count if hasattr(result, "count") else 0,
                }
            else:
                metrics = {
                    "status": "unavailable",
                    "backend": "supabase",
                    "document_count": 0,
                }

            logger.info("Database metrics: %s", metrics)
            return metrics
        except Exception as exc:
            logger.error("Failed to get database metrics: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve database metrics: {exc}",
            ) from exc

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "FORBIDDEN",
            500: "METRICS_DB_FETCH_FAILED",
        },
        logger=logger,
        operation_name="metrics db",
    )


@router.post("/log-error")
async def log_frontend_error(
    request: Request,
    error_data: dict,
    current_user=Depends(get_optional_user),
):
    async def operation():
        try:
            message = error_data.get("message", "Unknown frontend error")
            stack = error_data.get("stack", "No stack trace provided")
            url = error_data.get("url", "Unknown URL")
            timestamp = error_data.get("timestamp", "No timestamp provided")

            logger.error(
                "Frontend Error Captured:\nMessage: %s\nURL: %s\nTimestamp: %s\nStack: %s",
                message,
                url,
                timestamp,
                stack,
            )

            try:
                from app.middleware.prometheus_metrics import AGENT_TOOLS_USAGE_TOTAL

                AGENT_TOOLS_USAGE_TOTAL.labels(tool_name="frontend", status="error").inc()
            except ImportError:
                pass

            return {"status": "logged"}
        except Exception as exc:
            logger.error("Failed to log frontend error: %s", exc)
            return {"status": "error", "message": str(exc)}

    return await run_enveloped(
        request,
        operation,
        code_map={422: "INVALID_ERROR_PAYLOAD"},
        logger=logger,
        operation_name="metrics log error",
    )


@router.get("/health")
async def health_check(request: Request):
    async def operation():
        health_status = {
            "status": "healthy",
            "components": {
                "api": "healthy",
                "database": "unknown",
                "ai_models": "healthy",
            },
        }

        try:
            from app.services.llm_service import check_health as llm_check_health

            llm_health = await llm_check_health()
            health_status["components"]["llm_nvidia"] = llm_health.get("nvidia", "unknown")
            health_status["components"]["llm_deepseek"] = llm_health.get("deepseek", "unknown")

            if llm_health.get("nvidia") != "healthy" and llm_health.get("deepseek") != "healthy":
                health_status["status"] = "degraded"
        except Exception as exc:
            logger.error("LLM health check failed: %s", exc)

        try:
            sb = get_supabase_client()
            if sb:
                sb.table("documents").select("id", count="exact").limit(0).execute()
                health_status["components"]["database"] = "healthy"
            else:
                health_status["components"]["database"] = "unavailable"
                health_status["status"] = "degraded"
        except Exception as exc:
            logger.error("Database health check failed: %s", exc)
            health_status["components"]["database"] = "unhealthy"
            health_status["status"] = "degraded"

        return health_status

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="metrics health",
    )


@router.get("/dashboard")
async def get_metrics_dashboard(
    request: Request,
    admin_user=Depends(require_role("admin")),
) -> Dict[str, Any]:
    async def operation():
        model_metrics = get_model_metrics()
        ab_testing = get_ab_testing()
        sb = get_supabase_client()
        db_status = "connected" if sb is not None else "disconnected"
        db_ab_tests = 0
        db_model_metrics = 0

        try:
            if sb:
                res_metrics = sb.table("model_metrics").select("id", count="exact").limit(1).execute()
                db_model_metrics = res_metrics.count if res_metrics else 0

                res_ab = sb.table("ab_test_results").select("id", count="exact").limit(1).execute()
                db_ab_tests = res_ab.count if res_ab else 0
        except Exception as exc:
            logger.warning("Failed to query metrics counts from Supabase: %s", exc)

        return {
            "status": "success",
            "persistent_db_status": db_status,
            "database_records": {
                "model_metrics_count": db_model_metrics,
                "ab_test_results_count": db_ab_tests,
            },
            "live_metrics_summary": model_metrics.get_summary(),
            "live_model_comparison": model_metrics.get_model_comparison(),
            "live_ab_test_summary": ab_testing.get_test_summary(),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={
            403: "FORBIDDEN",
            500: "METRICS_DASHBOARD_FAILED",
        },
        logger=logger,
        operation_name="metrics dashboard",
    )


@router.get("/enhancements")
async def get_enhancement_metrics(
    request: Request,
    admin_user=Depends(require_role("admin")),
) -> Dict[str, Any]:
    async def operation():
        profile = enhancement_manager.refresh()
        profile_dict = profile.to_dict()
        return {
            "status": "success",
            "enhancements_enabled": bool(profile_dict.get("enabled")),
            "queue_mode": profile_dict.get("queue_provider"),
            "queue_ready": bool(profile_dict.get("queue_available")),
            "ocr_backends": profile_dict.get("ocr_backends", []),
            "keyword_backends": profile_dict.get("keyword_backends", []),
            "profile": profile_dict,
        }

    return await run_enveloped(
        request,
        operation,
        code_map={403: "FORBIDDEN"},
        logger=logger,
        operation_name="metrics enhancements",
    )


@router.get("/vllm-readiness")
async def get_vllm_readiness(
    request: Request,
    admin_user=Depends(require_role("admin")),
) -> Dict[str, Any]:
    async def operation():
        return {
            "status": "success",
            "report": build_vllm_adoption_report(),
        }

    return await run_enveloped(
        request,
        operation,
        code_map={403: "FORBIDDEN"},
        logger=logger,
        operation_name="metrics vllm readiness",
    )
