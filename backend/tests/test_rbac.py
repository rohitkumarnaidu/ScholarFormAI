# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.middleware.rbac import require_role, resolve_user_role
from app.utils.dependencies import get_current_user


def _user(*, role: str, app_metadata: dict | None = None):
    return SimpleNamespace(role=role, app_metadata=app_metadata or {})


def test_resolve_user_role_from_metadata_plan_tier():
    user = _user(role="authenticated", app_metadata={"plan_tier": "pro"})
    assert resolve_user_role(user) == "pro"


def test_require_role_allows_higher_tier_user():
    guard = require_role("pro")
    user = _user(role="admin")
    assert guard(current_user=user) is user


def test_require_role_denies_lower_tier_user():
    guard = require_role("admin")
    user = _user(role="free")
    try:
        guard(current_user=user)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
        assert "admin" in str(getattr(exc, "detail", ""))
    else:
        raise AssertionError("Expected HTTP 403 for insufficient role.")


def test_require_role_treats_service_role_as_admin():
    guard = require_role("admin")
    user = _user(role="service_role")
    assert guard(current_user=user) is user


def test_require_role_dependency_enforced_by_fastapi():
    app = FastAPI()

    @app.get("/admin")
    def admin_route(current_user=Depends(require_role("admin"))):
        return {"role": getattr(current_user, "role", "")}

    app.dependency_overrides[get_current_user] = lambda: _user(role="free")
    with TestClient(app) as client:
        denied = client.get("/admin")
        assert denied.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: _user(role="admin")
    with TestClient(app) as client:
        allowed = client.get("/admin")
        assert allowed.status_code == 200
        assert allowed.json()["role"] == "admin"
