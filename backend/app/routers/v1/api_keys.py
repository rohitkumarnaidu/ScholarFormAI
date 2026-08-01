# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
API Key management router — /api/v1/keys
Handles CRUD for user-provided LLM provider API keys with rate limiting.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.dependencies import get_current_user
from app.services.api_key_service import ApiKeyService
from app.services.api_key_rate_limiter import get_api_key_rate_limiter, RateLimitResult

logger = logging.getLogger(__name__)

router = APIRouter(tags=["api-keys"])


# --- Pydantic Schemas ---


class CreateApiKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider name (openai, anthropic, deepseek, etc.)")
    api_key: str = Field(..., min_length=8, description="Raw API key value")
    key_label: Optional[str] = Field(None, max_length=100, description="Friendly label for the key")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=100000)
    daily_quota: Optional[int] = Field(None, ge=1, le=1000000)


class UpdateApiKeyRequest(BaseModel):
    key_label: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=100000)
    daily_quota: Optional[int] = Field(None, ge=1, le=1000000)


class TestApiKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider name")
    api_key: str = Field(..., min_length=8, description="Raw API key to test")


class ApiKeyResponse(BaseModel):
    id: str
    provider: str
    key_label: Optional[str]
    is_active: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    daily_quota: int
    total_requests: int
    last_request_at: Optional[str]
    created_at: Optional[str]
    key_preview: str


class UsageStatsResponse(BaseModel):
    provider: str
    total_requests: int
    total_tokens: int
    avg_response_time_ms: float


class ProviderInfo(BaseModel):
    name: str
    default_rpm: int
    default_rph: int
    default_daily: int


# --- Endpoints ---


@router.post("", response_model=ApiKeyResponse, status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    try:
        key = service.create_key(
            user_id=str(user.id),
            provider=request.provider,
            api_key=request.api_key,
            key_label=request.key_label,
            rate_limit_per_minute=request.rate_limit_per_minute,
            rate_limit_per_hour=request.rate_limit_per_hour,
            daily_quota=request.daily_quota,
        )
        rate_limiter = get_api_key_rate_limiter()
        result = rate_limiter.check_rate_limit(str(key.id))
        apply_rate_limit_headers(response, result)
        return ApiKeyResponse(**key.to_dict(mask_key=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    provider: Optional[str] = Query(None, description="Filter by provider"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    keys = service.list_keys(user_id=str(user.id), provider=provider)
    return [ApiKeyResponse(**k.to_dict(mask_key=True)) for k in keys]


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    key = service.get_key(key_id, str(user.id))
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    rate_limiter = get_api_key_rate_limiter()
    apply_rate_limit_headers(response, rate_limiter.check_rate_limit(key_id))
    return ApiKeyResponse(**key.to_dict(mask_key=True))


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateApiKeyRequest,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    key = service.update_key(
        key_id=key_id,
        user_id=str(user.id),
        key_label=request.key_label,
        is_active=request.is_active,
        rate_limit_per_minute=request.rate_limit_per_minute,
        rate_limit_per_hour=request.rate_limit_per_hour,
        daily_quota=request.daily_quota,
    )
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    rate_limiter = get_api_key_rate_limiter()
    apply_rate_limit_headers(response, rate_limiter.check_rate_limit(key_id))
    return ApiKeyResponse(**key.to_dict(mask_key=True))


@router.delete("/{key_id}", status_code=204)
async def delete_api_key(
    key_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    deleted = service.delete_key(key_id, str(user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
    rate_limiter = get_api_key_rate_limiter()
    apply_rate_limit_headers(response, rate_limiter.check_rate_limit(key_id))


@router.get("/usage", response_model=dict[str, UsageStatsResponse])
async def get_usage_stats(
    hours: int = Query(24, ge=1, le=720, description="Hours of history (1-720)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    stats = service.get_usage_stats(user_id=str(user.id), hours=hours)
    return {provider: UsageStatsResponse(provider=provider, **data) for provider, data in stats.items()}


@router.get("/{key_id}/usage", response_model=dict)
async def get_key_usage(
    key_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    service = ApiKeyService(db)
    key = service.get_key(key_id, str(user.id))
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    rate_limiter = get_api_key_rate_limiter()
    usage = rate_limiter.get_usage(key_id)
    return {
        "key_id": key_id,
        "total_requests": key.total_requests,
        "last_request_at": key.last_request_at.isoformat() if key.last_request_at else None,
        "rate_limits": {
            "per_minute": key.rate_limit_per_minute,
            "per_hour": key.rate_limit_per_hour,
            "per_day": key.daily_quota,
        },
        "current_usage": usage,
    }


@router.get("/providers", response_model=dict[str, ProviderInfo])
async def get_supported_providers():
    providers = ApiKeyService.get_supported_providers()
    return {name: ProviderInfo(**info) for name, info in providers.items()}


@router.post("/test", response_model=dict)
async def test_api_key(
    request: TestApiKeyRequest,
    user=Depends(get_current_user),
):
    """Test API key connectivity without storing it."""
    provider = request.provider.lower()
    api_key = request.api_key

    test_results = {
        "provider": provider,
        "status": "unknown",
        "message": "",
        "response_time_ms": 0,
    }

    start = time.time()
    try:
        from app.services.provider_registry import BUILTIN_PROVIDERS

        info = BUILTIN_PROVIDERS.get(provider)
        if info:
            base = info.get("base_url", "")
            api_base = base() if callable(base) else base
        elif provider in {
            "openai",
            "anthropic",
            "groq",
            "deepseek",
            "openrouter",
            "google",
            "cohere",
            "mistral",
            "nvidia",
        }:
            lookup = {
                "openai": "https://api.openai.com/v1",
                "anthropic": "https://api.anthropic.com/v1",
                "groq": "https://api.groq.com/openai/v1",
                "deepseek": "https://api.deepseek.com",
                "openrouter": "https://openrouter.ai/api/v1",
                "google": "https://generativelanguage.googleapis.com/v1beta",
                "cohere": "https://api.cohere.com/v1",
                "mistral": "https://api.mistral.ai/v1",
                "nvidia": "https://integrate.api.nvidia.com/v1",
            }
            api_base = lookup[provider]
        else:
            test_results["status"] = "skipped"
            test_results["message"] = f"Unknown provider: {provider}"
            test_results["response_time_ms"] = round((time.time() - start) * 1000, 2)
            return test_results

        import httpx

        headers = {}
        if provider == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{api_base.rstrip('/')}/models" if provider != "ollama" else f"{api_base.rstrip('/')}/api/tags",
                headers=headers,
            )
            test_results["status"] = "valid" if resp.status_code == 200 else "invalid"
            test_results["message"] = resp.text[:200] if resp.status_code != 200 else "Connection successful"
    except Exception as e:
        test_results["status"] = "error"
        test_results["message"] = str(e)[:200]

    test_results["response_time_ms"] = round((time.time() - start) * 1000, 2)
    return test_results


def apply_rate_limit_headers(response, result: RateLimitResult):
    """Add rate limit headers to a response."""
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(result.reset_at))
    if result.retry_after is not None:
        response.headers["Retry-After"] = str(int(result.retry_after) + 1)
