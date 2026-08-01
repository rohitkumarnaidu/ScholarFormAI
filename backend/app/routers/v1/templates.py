# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.db.supabase_client import get_supabase_client
from app.pipeline.services.csl_fetcher import fetch_style, search_styles
from app.schemas.user import User
from app.services.audit_log_service import audit_log_service
from app.utils.dependencies import get_optional_user
from app.utils.logging_context import bind_request_context

from ._helpers import run_enveloped

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(bind_request_context)])


def _require_db():
    sb = get_supabase_client()
    if sb is None:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
        )
    return sb


def _require_user(current_user: User | None) -> User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


def _extract_template_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Invalid template payload")

    candidate = payload.get("template")
    template_data = candidate if isinstance(candidate, dict) else payload

    if not isinstance(template_data, dict):
        raise HTTPException(status_code=422, detail="Invalid template payload")

    name = str(template_data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Template name is required")

    config = template_data.get("config")
    if config is None:
        config = template_data.get("settings")
    if config is None:
        config = payload.get("config")
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise HTTPException(status_code=422, detail="Template config must be an object")

    description = template_data.get("description", payload.get("description", ""))
    if description is None:
        description = ""
    description = str(description)

    template_id = str(template_data.get("id") or payload.get("id") or uuid4())

    now_iso = datetime.now(UTC).isoformat()
    created_at = (
        template_data.get("created_at")
        or template_data.get("createdAt")
        or payload.get("created_at")
        or payload.get("createdAt")
        or now_iso
    )
    updated_at = now_iso

    return {
        "id": template_id,
        "name": name,
        "description": description,
        "config": config,
        "created_at": str(created_at),
        "updated_at": updated_at,
    }


def _canonical_template_id(raw_name: str) -> str:
    return "_".join(str(raw_name or "").strip().lower().split())


def _template_display_name(template_id: str) -> str:
    if template_id == "none":
        return "None"
    if template_id in {"ieee", "apa", "acm", "mla"}:
        return template_id.upper()
    return template_id.replace("_", " ").title()


async def _list_builtin_templates() -> dict[str, Any]:
    templates_dir = Path(__file__).resolve().parents[2] / "templates"
    descriptions = {
        "ieee": "IEEE manuscript style",
        "springer": "Springer journal style",
        "apa": "APA style",
        "nature": "Nature style",
        "vancouver": "Vancouver citation style",
        "resume": "Professional resume template",
        "portfolio": "Portfolio showcase template",
    }

    items = []
    if templates_dir.exists():
        for entry in sorted(templates_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("__"):
                template_id = _canonical_template_id(entry.name)
                items.append(
                    {
                        "id": template_id,
                        "name": _template_display_name(template_id),
                        "description": descriptions.get(
                            template_id,
                            f"{_template_display_name(template_id)} template",
                        ),
                        "source": "built_in",
                    }
                )

    return {"templates": items}


async def _csl_search(
    *,
    q: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    search_query = (q or query or "").strip()
    if not search_query:
        raise HTTPException(status_code=422, detail="q query parameter is required")

    results = await search_styles(search_query)
    return {"query": search_query, "results": results}


async def _fetch_csl_style(slug: str):
    try:
        style = await fetch_style(slug.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Failed to fetch CSL style '%s': %s", slug, exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch CSL style '{slug}'") from exc
    return style


async def _list_custom_templates(current_user: User | None = None) -> dict[str, Any]:
    user = _require_user(current_user)
    sb = _require_db()
    try:
        result = (
            sb.table("custom_templates")
            .select("*")
            .eq("user_id", str(user.id))
            .order("updated_at", desc=True)
            .execute()
        )
        return {"templates": result.data or []}
    except Exception as exc:
        logger.error("Failed to list custom templates: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list custom templates") from exc


async def _create_custom_template(
    *,
    request: Request,
    payload: dict[str, Any],
    current_user: User | None = None,
) -> dict[str, Any]:
    user = _require_user(current_user)
    sb = _require_db()
    record = _extract_template_payload(payload)
    record["user_id"] = str(user.id)

    try:
        result = sb.table("custom_templates").insert(record).execute()
        created = result.data[0] if result.data else record
        await audit_log_service.log(
            user_id=str(user.id),
            action="template_create",
            resource_type="template",
            resource_id=str(created.get("id") or record.get("id")),
            ip_address=request.client.host if request.client else None,
            details={"name": created.get("name")},
        )
        return {"template": created}
    except Exception as exc:
        logger.error("Failed to create custom template: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create custom template") from exc


async def _update_custom_template(
    *,
    request: Request,
    template_id: str,
    payload: dict[str, Any],
    current_user: User | None = None,
) -> dict[str, Any]:
    user = _require_user(current_user)
    sb = _require_db()
    parsed = _extract_template_payload(payload)

    updates = {
        "name": parsed["name"],
        "description": parsed["description"],
        "config": parsed["config"],
        "updated_at": datetime.now(UTC).isoformat(),
    }

    try:
        result = (
            sb.table("custom_templates").update(updates).eq("id", template_id).eq("user_id", str(user.id)).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Template not found")
        await audit_log_service.log(
            user_id=str(user.id),
            action="template_update",
            resource_type="template",
            resource_id=str(template_id),
            ip_address=request.client.host if request.client else None,
            details={"name": updates.get("name")},
        )
        return {"template": result.data[0]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update custom template %s: %s", template_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update custom template") from exc


async def _delete_custom_template(
    *,
    template_id: str,
    current_user: User | None = None,
) -> dict[str, Any]:
    user = _require_user(current_user)
    sb = _require_db()

    try:
        existing = (
            sb.table("custom_templates")
            .select("id")
            .eq("id", template_id)
            .eq("user_id", str(user.id))
            .maybe_single()
            .execute()
        )
        if not existing.data:
            raise HTTPException(status_code=404, detail="Template not found")

        sb.table("custom_templates").delete().eq("id", template_id).eq("user_id", str(user.id)).execute()
        return {"status": "deleted", "id": template_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete custom template %s: %s", template_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete custom template") from exc


@router.get("")
async def list_builtin_templates(request: Request):
    async def operation():
        return await _list_builtin_templates()

    return await run_enveloped(
        request,
        operation,
        logger=logger,
        operation_name="template list",
    )


@router.get("/csl/search")
async def csl_search(
    request: Request,
    q: str | None = Query(default=None, min_length=1),
    query: str | None = Query(default=None, min_length=1),
):
    async def operation():
        return await _csl_search(q=q, query=query)

    return await run_enveloped(
        request,
        operation,
        code_map={422: "INVALID_TEMPLATE_QUERY"},
        logger=logger,
        operation_name="template csl search",
    )


@router.get("/csl/fetch")
async def csl_fetch(
    request: Request,
    slug: str = Query(..., min_length=1),
):
    async def operation():
        return await _fetch_csl_style(slug)

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_STYLE_SLUG",
            502: "STYLE_FETCH_FAILED",
        },
        logger=logger,
        operation_name="template csl fetch",
    )


@router.get("/csl/{styleId}")
async def csl_fetch_by_style_id(
    request: Request,
    styleId: str,
):
    async def operation():
        return await _fetch_csl_style(styleId)

    return await run_enveloped(
        request,
        operation,
        code_map={
            400: "INVALID_STYLE_SLUG",
            502: "STYLE_FETCH_FAILED",
        },
        logger=logger,
        operation_name="template style fetch",
    )


@router.get("/custom")
async def list_custom_templates(
    request: Request,
    current_user: User | None = Depends(get_optional_user),
):
    async def operation():
        return await _list_custom_templates(current_user=current_user)

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            500: "TEMPLATE_LIST_FAILED",
        },
        logger=logger,
        operation_name="custom template list",
    )


@router.post("/custom")
async def create_custom_template(
    request: Request,
    payload: dict[str, Any],
    current_user: User | None = Depends(get_optional_user),
):
    async def operation():
        return await _create_custom_template(
            request=request,
            payload=payload,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            422: "INVALID_TEMPLATE_PAYLOAD",
            500: "TEMPLATE_CREATE_FAILED",
        },
        logger=logger,
        operation_name="custom template create",
    )


@router.put("/custom/{templateId}")
async def update_custom_template(
    request: Request,
    templateId: str,
    payload: dict[str, Any],
    current_user: User | None = Depends(get_optional_user),
):
    async def operation():
        return await _update_custom_template(
            request=request,
            template_id=templateId,
            payload=payload,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            404: "TEMPLATE_NOT_FOUND",
            422: "INVALID_TEMPLATE_PAYLOAD",
            500: "TEMPLATE_UPDATE_FAILED",
        },
        logger=logger,
        operation_name="custom template update",
    )


@router.delete("/custom/{templateId}")
async def delete_custom_template(
    request: Request,
    templateId: str,
    current_user: User | None = Depends(get_optional_user),
):
    async def operation():
        return await _delete_custom_template(
            template_id=templateId,
            current_user=current_user,
        )

    return await run_enveloped(
        request,
        operation,
        code_map={
            401: "UNAUTHORIZED",
            404: "TEMPLATE_NOT_FOUND",
            500: "TEMPLATE_DELETE_FAILED",
        },
        logger=logger,
        operation_name="custom template delete",
    )
