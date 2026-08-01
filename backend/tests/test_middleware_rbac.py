import pytest
from unittest.mock import MagicMock


class TestNormalizeRole:
    def test_normalized_lowercase(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("Admin") == "admin"

    def test_guest_alias_to_free(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("guest") == "free"

    def test_premium_alias_to_pro(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("premium") == "pro"

    def test_owner_alias_to_admin(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("owner") == "admin"

    def test_unknown_role_passed_through(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("custom_role") == "custom_role"

    def test_none_returns_empty_string(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role(None) == ""

    def test_empty_string(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("") == ""


class TestResolveUserRole:
    def test_defaults_to_free(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = None
        assert resolve_user_role(user) == "free"

    def test_direct_role(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = "admin"
        user.app_metadata = None
        assert resolve_user_role(user) == "admin"

    def test_app_metadata_role(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {"role": "pro"}
        assert resolve_user_role(user) == "pro"

    def test_app_metadata_plan_tier(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {"plan_tier": "admin"}
        assert resolve_user_role(user) == "admin"

    def test_highest_role_wins(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = "free"
        user.app_metadata = {"role": "pro", "plan_tier": "admin"}
        assert resolve_user_role(user) == "admin"

    def test_non_dict_app_metadata(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = "not a dict"
        assert resolve_user_role(user) == "free"


class TestRequireRole:
    def test_unsupported_role_raises(self):
        from app.middleware.rbac import require_role
        with pytest.raises(ValueError, match="Unsupported role"):
            require_role("nonexistent")

    def test_sufficient_permissions(self):
        from app.middleware.rbac import require_role
        guard = require_role("free")
        user = MagicMock()
        user.role = "admin"
        result = guard(current_user=user)
        assert result is user
        assert user.effective_role == "admin"

    def test_insufficient_permissions(self):
        from app.middleware.rbac import require_role
        from fastapi import HTTPException
        guard = require_role("admin")
        user = MagicMock()
        user.role = "free"
        with pytest.raises(HTTPException) as exc:
            guard(current_user=user)
        assert exc.value.status_code == 403
