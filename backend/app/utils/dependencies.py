# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

import logging

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.user import User
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> User:
    """
    FastAPI dependency to extract and verify the user from the Authorization Bearer header.
    """
    token = None
    if credentials:
        token = credentials.credentials

    if not token:
        # Explicitly reject query parameter tokens for security
        if request.query_params.get("token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tokens via query parameter are not supported for security reasons. Use the Authorization: Bearer header instead.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = AuthService.decode_token(token)
        user_id = AuthService.get_user_id_from_payload(payload)

        email = payload.get("email")
        role = payload.get("role", "authenticated")
        app_metadata = payload.get("app_metadata")

        try:
            from app.middleware.prometheus_metrics import MetricsManager

            MetricsManager.record_user_activity(str(user_id))
        except Exception:
            pass  # intentionally ignored

        return User(id=user_id, email=email, role=role, app_metadata=app_metadata)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, HTTPException) as err:
        logger.warning("Authentication failed: %s", str(err))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def get_optional_user(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
) -> User | None:
    """
    FastAPI dependency that returns a User if a valid Bearer token is present,
    otherwise returns None.
    """
    token = None
    if credentials:
        token = credentials.credentials

    if not token:
        return None

    try:
        payload = AuthService.decode_token(token)
        user_id = AuthService.get_user_id_from_payload(payload)
        email = payload.get("email")
        role = payload.get("role", "authenticated")
        app_metadata = payload.get("app_metadata")
        try:
            from app.middleware.prometheus_metrics import MetricsManager

            MetricsManager.record_user_activity(str(user_id))
        except Exception:
            pass  # intentionally ignored
        return User(id=user_id, email=email, role=role, app_metadata=app_metadata)
    except Exception as e:
        logger.warning("Optional token validation failed: %s", str(e))
        return None


def _has_admin_scope(user: User) -> bool:
    role = str(getattr(user, "role", "") or "").strip().lower()
    if role in {"admin", "service_role"}:
        return True

    app_metadata = getattr(user, "app_metadata", None)
    if not isinstance(app_metadata, dict):
        return False

    metadata_role = app_metadata.get("role")
    if isinstance(metadata_role, str) and metadata_role.strip().lower() == "admin":
        return True

    metadata_roles = app_metadata.get("roles")
    if isinstance(metadata_roles, str):
        return metadata_roles.strip().lower() == "admin"
    if isinstance(metadata_roles, list):
        normalized = {str(item).strip().lower() for item in metadata_roles}
        return "admin" in normalized

    return False


def require_admin_user(user: User = Depends(get_current_user)) -> User:
    if not _has_admin_scope(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


class RequireRole:
    """
    Dependency factory for strict RBAC.
    Usage:
        @router.get("/protected", dependencies=[Depends(RequireRole({"editor", "manager"}))])
    """

    def __init__(self, allowed_roles: set[str]):
        self.allowed_roles = {r.lower() for r in allowed_roles}

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_roles = set()

        # Base role
        if getattr(user, "role", None):
            user_roles.add(str(user.role).strip().lower())

        # App metadata roles
        app_meta = getattr(user, "app_metadata", {})
        if isinstance(app_meta, dict):
            if isinstance(app_meta.get("role"), str):
                user_roles.add(app_meta.get("role").strip().lower())
            roles = app_meta.get("roles")
            if isinstance(roles, str):
                user_roles.add(roles.strip().lower())
            elif isinstance(roles, list):
                for r in roles:
                    user_roles.add(str(r).strip().lower())

        # Admin / System accounts bypass specific role checks
        if "admin" in user_roles or "service_role" in user_roles:
            return user

        if not self.allowed_roles.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Access forbidden: requires one of {self.allowed_roles}"
            )
        return user
