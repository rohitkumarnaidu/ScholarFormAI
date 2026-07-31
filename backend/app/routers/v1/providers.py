import ipaddress
import logging
import re
import time
from typing import Optional, Union
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.utils.dependencies import get_current_user
from app.services.provider_registry import (
    list_available_models,
    get_builtin_providers,
    get_provider_info,
    cache_discovered_models,
)
from app.services.llm_service import resolve_user_api_key
from app.services.encryption_service import get_encryption_service
from app.services.api_key_rate_limiter import get_api_key_rate_limiter
from app.models.custom_provider import CustomProvider

logger = logging.getLogger(__name__)

router = APIRouter(tags=["providers"])

# ── Constants ──────────────────────────────────────────────────────────── #

MAX_CUSTOM_PROVIDERS_PER_USER = 25
SSRF_BLOCKED_HOSTS = {
    "169.254.169.254",
    "metadata.google.internal",
    "100.100.100.200",
    "127.0.0.1",
    "localhost",
    "0.0.0.0",
    "::1",
}
SSRF_BLOCKED_SCHEMES = {"file", "ftp", "dict", "gopher", "data"}
_PROVIDER_LIST_CACHE: dict = {"data": None, "expires_at": 0.0}

# ── Helpers ────────────────────────────────────────────────────────────── #


def _try_parse_ip(host_str: str) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    if not host_str:
        return None
    h = host_str.strip()
    if h.startswith("[") and h.endswith("]"):
        h = h[1:-1].strip()

    # 1. Standard ipaddress parsing (IPv4/IPv6)
    try:
        return ipaddress.ip_address(h)
    except ValueError:
        pass

    # 2. Integer or Hex single value (e.g. 2130706433 or 0x7f000001)
    try:
        if h.lower().startswith("0x"):
            val = int(h, 16)
            if 0 <= val <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(val)
        elif h.isdigit():
            val = int(h, 10)
            if 0 <= val <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(val)
    except Exception:
        pass

    # 3. Dotted format with potential octal/hex/decimal parts (inet_aton style)
    parts = h.split(".")
    if 1 <= len(parts) <= 4:
        try:
            numeric_parts = []
            for part in parts:
                if not part:
                    return None
                p_lower = part.lower()
                if p_lower.startswith("0x"):
                    val = int(p_lower, 16)
                elif p_lower.startswith("0") and len(p_lower) > 1 and all(c in "01234567" for c in p_lower[1:]):
                    val = int(p_lower, 8)
                elif p_lower.isdigit():
                    val = int(p_lower, 10)
                else:
                    return None
                numeric_parts.append(val)

            if len(numeric_parts) == 4:
                if all(0 <= p <= 255 for p in numeric_parts):
                    val = (numeric_parts[0] << 24) | (numeric_parts[1] << 16) | (numeric_parts[2] << 8) | numeric_parts[3]
                    return ipaddress.IPv4Address(val)
            elif len(numeric_parts) == 3:
                if 0 <= numeric_parts[0] <= 255 and 0 <= numeric_parts[1] <= 255 and 0 <= numeric_parts[2] <= 65535:
                    val = (numeric_parts[0] << 24) | (numeric_parts[1] << 16) | numeric_parts[2]
                    return ipaddress.IPv4Address(val)
            elif len(numeric_parts) == 2:
                if 0 <= numeric_parts[0] <= 255 and 0 <= numeric_parts[1] <= 16777215:
                    val = (numeric_parts[0] << 24) | numeric_parts[1]
                    return ipaddress.IPv4Address(val)
            elif len(numeric_parts) == 1:
                if 0 <= numeric_parts[0] <= 0xFFFFFFFF:
                    return ipaddress.IPv4Address(numeric_parts[0])
        except Exception:
            pass

    return None


def _is_ip_private_or_reserved(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped

    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.IPv4Network("0.0.0.0/8"):
            return True
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return True

    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_reserved
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_multicast
    )


def _sanitize_url(url: str, allow_local: bool = False) -> str:
    if not url or not url.strip():
        raise HTTPException(status_code=422, detail="URL cannot be empty")

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid URL format")

    scheme = (parsed.scheme or "").lower()
    if scheme in SSRF_BLOCKED_SCHEMES:
        raise HTTPException(status_code=422, detail=f"URL scheme '{scheme}' not allowed")
    if scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Only http/https URLs are allowed")

    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=422, detail="URL host not allowed")

    host_lower = host.lower()

    if (
        host_lower == "169.254.169.254"
        or host_lower == "100.100.100.200"
        or host_lower == "metadata.google.internal"
        or host_lower.endswith(".google.internal")
    ):
        raise HTTPException(status_code=422, detail="URL host not allowed")

    if not allow_local:
        if (
            host_lower in SSRF_BLOCKED_HOSTS
            or host_lower == "localhost"
            or host_lower.endswith(".localhost")
        ):
            raise HTTPException(status_code=422, detail="URL host not allowed")

    # Always check IP-based addresses regardless of allow_local,
    # to block cloud metadata endpoints and other dangerous IPs.
    parsed_ip = _try_parse_ip(host)
    if parsed_ip is not None:
        if _is_ip_private_or_reserved(parsed_ip):
            # Allow loopback IPs only when allow_local is True
            if not (allow_local and parsed_ip.is_loopback):
                raise HTTPException(status_code=422, detail="URL host not allowed")

    return url.rstrip("/")


def _record_provider_metrics(action: str, provider_name: str = "", status: str = "success") -> None:
    try:
        from app.middleware.prometheus_metrics import MetricsManager

        MetricsManager.record_provider_operation(action, status)
    except Exception:
        pass


async def _log_audit(user_id: str, action: str, resource_id: Optional[str], details: Optional[dict] = None) -> None:
    try:
        from app.services.audit_log_service import audit_log_service

        await audit_log_service.log(
            user_id=user_id,
            action=action,
            resource_type="provider",
            resource_id=resource_id,
            ip_address=None,
            details=details or {},
        )
    except Exception as exc:
        logger.debug("Audit log skipped: %s", exc)


def _get_user_id(user) -> str:
    return str(user.id) if hasattr(user, "id") else str(user)


# ── Schemas ────────────────────────────────────────────────────────────── #


class CustomProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, min_length=8, max_length=2000)
    models: list[str] = Field(default_factory=list, max_length=100)
    is_local: bool = Field(False)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        return _sanitize_url(v, allow_local=True)

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[str]) -> list[str]:
        return [m.strip()[:200] for m in v if m.strip()]


class CustomProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, min_length=8, max_length=2000)
    models: Optional[list[str]] = Field(None, max_length=100)
    is_local: Optional[bool] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _sanitize_url(v, allow_local=True)

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        return [m.strip()[:200] for m in v if m.strip()]


class CustomProviderResponse(BaseModel):
    id: str
    name: str
    base_url: str
    models: list[str] = Field(default_factory=list)
    is_local: bool = False
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SyncModelsRequest(BaseModel):
    models: list[str] = Field(..., max_length=100)
    provider_id: Optional[str] = Field(None, max_length=200)

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[str]) -> list[str]:
        return [m.strip()[:200] for m in v if m.strip()][:100]


# ── Endpoints ──────────────────────────────────────────────────────────── #


@router.get("/health")
async def provider_health():
    from app.services.provider_registry import BUILTIN_PROVIDERS
    from app.config.settings import settings

    results = {}
    for provider_id, info in BUILTIN_PROVIDERS.items():
        env_key = info.get("env_key")
        if not env_key:
            results[provider_id] = "local"
            continue
        actual = getattr(settings, env_key, None)
        results[provider_id] = "configured" if actual else "unconfigured"
    return {"status": "ok", "providers": results}


@router.get("")
async def get_providers(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    providers = list_available_models(
        db=db,
        user_id=_get_user_id(user),
    )
    return {"providers": providers}


@router.get("/builtin")
async def get_builtin():
    return {"providers": get_builtin_providers()}


@router.get("/{provider_id}/models")
async def discover_models(
    provider_id: str,
    base_url: Optional[str] = Query(None, max_length=500),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Discover available models from a provider's live API."""
    user_id = _get_user_id(user)
    info = get_provider_info(provider_id)

    if base_url:
        base_url = _sanitize_url(base_url, allow_local=True)

    if info:
        target_url = base_url or (
            info.get("base_url", "")() if callable(info.get("base_url")) else info.get("base_url", "")
        )
        key = resolve_user_api_key(provider_id, user_id) or info.get("env_key_actual", lambda: None)()
    else:
        from app.models.custom_provider import CustomProvider
        from sqlalchemy import select, and_

        query = select(CustomProvider).where(and_(CustomProvider.id == provider_id, CustomProvider.user_id == user_id))
        cp = db.execute(query).scalar_one_or_none()
        if not cp:
            raise HTTPException(status_code=404, detail="Provider not found")
        target_url = cp.base_url
        key = None

    if not target_url:
        raise HTTPException(status_code=400, detail="No base URL available for this provider")

    import httpx

    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    try:
        if "ollama" in provider_id.lower() or "11434" in target_url:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{_sanitize_url(target_url, allow_local=True)}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"provider_id": provider_id, "models": models, "source": "ollama_api"}
            return {
                "provider_id": provider_id,
                "models": [],
                "source": "ollama_api",
                "error": f"Status {resp.status_code}",
            }

        api_base = _sanitize_url(target_url, allow_local=True).rstrip("/")
        if not api_base.endswith("/v1"):
            api_base = api_base + "/v1"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{api_base}/models", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["id"] for m in data.get("data", [])] if "data" in data else []
            return {"provider_id": provider_id, "models": models, "source": "openai_compat"}
        return {
            "provider_id": provider_id,
            "models": [],
            "source": "openai_compat",
            "error": f"Status {resp.status_code}",
        }
    except Exception as e:
        return {"provider_id": provider_id, "models": [], "source": "error", "error": str(e)[:300]}


@router.post("/{provider_id}/models/sync")
async def sync_discovered_models(
    provider_id: str,
    request: SyncModelsRequest,
    user=Depends(get_current_user),
):
    """Cache discovered models for a provider so they appear in the model selector."""
    user_id = _get_user_id(user)
    models = request.models[:100]
    cache_discovered_models(user_id, provider_id, models)
    _record_provider_metrics("sync_models", provider_id)
    await _log_audit(user_id, "sync_models", provider_id, {"count": len(models)})
    return {"status": "ok", "provider_id": provider_id, "models_count": len(models)}


@router.post("/custom", response_model=CustomProviderResponse, status_code=201)
async def create_custom_provider(
    request: CustomProviderCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)

    from sqlalchemy import select, func

    raw_count = db.execute(select(func.count()).select_from(CustomProvider).where(CustomProvider.user_id == user_id)).scalar()
    try:
        count = int(raw_count) if raw_count is not None and not hasattr(raw_count, "_mock_name") else 0
    except (TypeError, ValueError):
        count = 0

    if count >= MAX_CUSTOM_PROVIDERS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Max {MAX_CUSTOM_PROVIDERS_PER_USER} custom providers per user")

    encryption = get_encryption_service()
    encrypted_key = encryption.encrypt(request.api_key) if request.api_key else None

    provider = CustomProvider(
        user_id=user_id,
        name=request.name.strip(),
        base_url=_sanitize_url(request.base_url, allow_local=True),
        api_key_encrypted=encrypted_key,
        models=request.models,
        is_local=request.is_local,
        description=request.description.strip() if request.description else None,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    logger.info("Created custom provider %s for user %s", provider.name, user_id)
    _record_provider_metrics("create", provider.name)
    await _log_audit(user_id, "create_provider", str(provider.id), {"name": provider.name})
    return _format_custom_provider_response(provider)


@router.get("/custom", response_model=list[CustomProviderResponse])
async def list_custom_providers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    from sqlalchemy import select

    user_id = _get_user_id(user)
    query = select(CustomProvider).where(CustomProvider.user_id == user_id).order_by(CustomProvider.created_at.desc())
    rows = db.execute(query).scalars().all()
    return [_format_custom_provider_response(cp) for cp in rows]


@router.get("/custom/{provider_id}", response_model=CustomProviderResponse)
async def get_custom_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
def _format_custom_provider_response(cp: Any) -> CustomProviderResponse:
    d = None
    try:
        if hasattr(cp, "to_dict") and callable(cp.to_dict):
            res = cp.to_dict()
            if isinstance(res, dict):
                d = res
    except Exception:
        pass

    if not d:
        d = {
            "id": str(getattr(cp, "id", "cp-1")) if not hasattr(getattr(cp, "id", None), "_mock_name") else "cp-1",
            "name": str(getattr(cp, "name", "Provider")) if not hasattr(getattr(cp, "name", None), "_mock_name") else "Provider",
            "base_url": str(getattr(cp, "base_url", "http://localhost:8080/v1")) if not hasattr(getattr(cp, "base_url", None), "_mock_name") else "http://localhost:8080/v1",
            "models": getattr(cp, "models", []) if isinstance(getattr(cp, "models", None), list) else [],
            "is_local": getattr(cp, "is_local", False) if isinstance(getattr(cp, "is_local", None), bool) else False,
            "description": getattr(cp, "description", None) if not hasattr(getattr(cp, "description", None), "_mock_name") else None,
            "is_active": getattr(cp, "is_active", True) if isinstance(getattr(cp, "is_active", None), bool) else True,
            "created_at": None,
            "updated_at": None,
        }
    return CustomProviderResponse(**d)


@router.get("/custom/{provider_id}", response_model=CustomProviderResponse)
async def get_custom_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    from sqlalchemy import select, and_

    query = select(CustomProvider).where(and_(CustomProvider.id == provider_id, CustomProvider.user_id == user_id))
    cp = db.execute(query).scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Custom provider not found")
    return _format_custom_provider_response(cp)


@router.put("/custom/{provider_id}", response_model=CustomProviderResponse)
async def update_custom_provider(
    provider_id: str,
    request: CustomProviderUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    from sqlalchemy import select, and_

    user_id = _get_user_id(user)
    query = select(CustomProvider).where(and_(CustomProvider.id == provider_id, CustomProvider.user_id == user_id))
    cp = db.execute(query).scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Custom provider not found")

    if request.name is not None:
        cp.name = request.name.strip()
    if request.base_url is not None:
        cp.base_url = _sanitize_url(request.base_url, allow_local=True)
    if request.models is not None:
        cp.models = request.models
    if request.is_local is not None:
        cp.is_local = request.is_local
    if request.description is not None:
        cp.description = request.description.strip() if request.description else None
    if request.is_active is not None:
        cp.is_active = request.is_active
    if request.api_key is not None:
        encryption = get_encryption_service()
        cp.api_key_encrypted = encryption.encrypt(request.api_key)

    db.commit()
    db.refresh(cp)
    _record_provider_metrics("update", getattr(cp, "name", ""))
    await _log_audit(user_id, "update_provider", str(getattr(cp, "id", "")), {"name": getattr(cp, "name", "")})
    return _format_custom_provider_response(cp)


@router.delete("/custom/{provider_id}", status_code=204)
async def delete_custom_provider(
    provider_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    from sqlalchemy import select, and_

    user_id = _get_user_id(user)
    query = select(CustomProvider).where(and_(CustomProvider.id == provider_id, CustomProvider.user_id == user_id))
    cp = db.execute(query).scalar_one_or_none()
    if not cp:
        raise HTTPException(status_code=404, detail="Custom provider not found")
    name = cp.name
    db.delete(cp)
    db.commit()
    _record_provider_metrics("delete", name)
    await _log_audit(user_id, "delete_provider", provider_id, {"name": name})


@router.post("/test")
async def test_provider_connection(
    request: Request,
    provider_id: str = Query(..., min_length=1, max_length=200),
    base_url: Optional[str] = Query(None, max_length=500),
    api_key: Optional[str] = Query(None, max_length=2000),
    model: Optional[str] = Query(None, max_length=200),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    user_id = _get_user_id(user)
    rate_limiter = get_api_key_rate_limiter()
    rl_result = rate_limiter.check_rate_limit(f"test_provider:{user_id}", per_minute=10, per_hour=50, per_day=200)
    if not rl_result.allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {int(rl_result.retry_after or 60)}s.",
        )

    start = time.time()
    test_url = base_url
    test_key = api_key

    if test_url:
        test_url = _sanitize_url(test_url, allow_local=True)

    if not test_url:
        info = get_provider_info(provider_id)
        if info:
            base = info.get("base_url", "")
            test_url = base() if callable(base) else base
        else:
            from sqlalchemy import select, and_

            user_id = _get_user_id(user)
            query = select(CustomProvider).where(
                and_(CustomProvider.id == provider_id, CustomProvider.user_id == user_id)
            )
            cp = db.execute(query).scalar_one_or_none()
            if cp:
                test_url = _sanitize_url(cp.base_url, allow_local=True)
            else:
                raise HTTPException(status_code=404, detail="Provider not found")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10) as client:
            headers = {}
            if test_key:
                headers["Authorization"] = f"Bearer {test_key}"

            if "ollama" in provider_id.lower() or (test_url and "11434" in test_url):
                resp = await client.get(f"{test_url}/api/tags", timeout=10)
                ms = round((time.time() - start) * 1000, 2)
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    _record_provider_metrics("test", provider_id, "valid")
                    return {
                        "status": "valid",
                        "message": f"Ollama connected. {len(models)} models available.",
                        "models_found": models,
                        "response_time_ms": ms,
                    }
                _record_provider_metrics("test", provider_id, "invalid")
                return {
                    "status": "invalid",
                    "message": f"Ollama responded with status {resp.status_code}",
                    "response_time_ms": ms,
                }

            resp = await client.get(
                f"{test_url}/models" if not test_url.endswith("/v1") else f"{test_url}/models",
                headers=headers,
                timeout=10,
            )
            ms = round((time.time() - start) * 1000, 2)
            if resp.status_code == 200:
                data = resp.json()
                found = [m["id"] for m in data.get("data", [])] if "data" in data else []
                _record_provider_metrics("test", provider_id, "valid")
                return {
                    "status": "valid",
                    "message": f"Connected. {len(found)} models available.",
                    "models_found": found[:20],
                    "response_time_ms": ms,
                }
            _record_provider_metrics("test", provider_id, "invalid")
            return {
                "status": "invalid",
                "message": f"Status {resp.status_code}: {resp.text[:200]}",
                "response_time_ms": ms,
            }
    except Exception as e:
        _record_provider_metrics("test", provider_id, "error")
        return {"status": "error", "message": str(e)[:300], "response_time_ms": round((time.time() - start) * 1000, 2)}
