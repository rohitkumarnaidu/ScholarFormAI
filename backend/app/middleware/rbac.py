# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status

from app.utils.dependencies import get_current_user

ROLE_HIERARCHY = {
    "free": 1,
    "pro": 2,
    "admin": 3,
}

ROLE_ALIASES = {
    "guest": "free",
    "authenticated": "free",
    "user": "free",
    "basic": "free",
    "trial": "pro",
    "premium": "pro",
    "paid": "pro",
    "service_role": "admin",
    "owner": "admin",
    "superadmin": "admin",
}


def _normalize_role(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return ROLE_ALIASES.get(normalized, normalized)


def resolve_user_role(current_user: Any) -> str:
    """
    Resolve a role from common user fields and metadata.
    Defaults to free for unknown or missing role values.
    """
    candidates = [getattr(current_user, "role", None)]

    app_metadata = getattr(current_user, "app_metadata", None)
    if isinstance(app_metadata, dict):
        candidates.extend(
            [
                app_metadata.get("role"),
                app_metadata.get("plan_tier"),
                app_metadata.get("tier"),
                app_metadata.get("subscription_tier"),
            ]
        )

    resolved = "free"
    for candidate in candidates:
        normalized = _normalize_role(candidate)
        if normalized in ROLE_HIERARCHY and ROLE_HIERARCHY[normalized] > ROLE_HIERARCHY[resolved]:
            resolved = normalized

    return resolved


def require_role(role: str):
    required_role = _normalize_role(role)
    if required_role not in ROLE_HIERARCHY:
        raise ValueError(f"Unsupported role '{role}'. Expected one of: {', '.join(sorted(ROLE_HIERARCHY))}")

    def _guard(current_user=Depends(get_current_user)):
        user_role = resolve_user_role(current_user)
        if ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[required_role]:
            setattr(current_user, "effective_role", user_role)
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions: '{required_role}' role required.",
        )

    return _guard
