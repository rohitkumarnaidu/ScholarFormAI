from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt
import pytest


class TestDependencies:
    def test_get_current_user_no_credentials(self):
        from fastapi import HTTPException

        from app.utils.dependencies import get_current_user

        request = MagicMock()
        request.query_params.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            get_current_user(request, None)
        assert exc.value.status_code == 401

    def test_get_current_user_query_token_rejected(self):
        from fastapi import HTTPException

        from app.utils.dependencies import get_current_user

        request = MagicMock()
        request.query_params.get.return_value = "some_token"
        with pytest.raises(HTTPException) as exc:
            get_current_user(request, None)
        assert "query parameter" in str(exc.value.detail).lower()

    def test_get_current_user_valid_token(self):
        from app.utils.dependencies import get_current_user

        credentials = MagicMock()
        credentials.credentials = "valid_token"
        request = MagicMock()
        request.query_params.get.return_value = None
        with patch(
            "app.utils.dependencies.AuthService.decode_token",
            return_value={"email": "test@test.com", "role": "authenticated", "app_metadata": {}},
        ):
            with patch("app.utils.dependencies.AuthService.get_user_id_from_payload", return_value="user_1"):
                user = get_current_user(request, credentials)
                assert user.id == "user_1"
                assert user.email == "test@test.com"

    def test_get_current_user_expired_token(self):
        from fastapi import HTTPException

        from app.utils.dependencies import get_current_user

        credentials = MagicMock()
        credentials.credentials = "expired"
        request = MagicMock()
        request.query_params.get.return_value = None
        with patch("app.utils.dependencies.AuthService.decode_token", side_effect=jwt.ExpiredSignatureError("expired")):
            with pytest.raises(HTTPException) as exc:
                get_current_user(request, credentials)
            assert exc.value.status_code == 401

    def test_get_optional_user_no_credentials(self):
        from app.utils.dependencies import get_optional_user

        request = MagicMock()
        result = get_optional_user(request, None)
        assert result is None

    def test_get_optional_user_valid(self):
        from app.utils.dependencies import get_optional_user

        credentials = MagicMock()
        credentials.credentials = "valid"
        request = MagicMock()
        with patch(
            "app.utils.dependencies.AuthService.decode_token",
            return_value={"email": "a@b.com", "role": "user", "app_metadata": {}},
        ):
            with patch("app.utils.dependencies.AuthService.get_user_id_from_payload", return_value="u1"):
                user = get_optional_user(request, credentials)
                assert user is not None

    def test_get_optional_user_failure_returns_none(self):
        from app.utils.dependencies import get_optional_user

        credentials = MagicMock()
        credentials.credentials = "bad"
        request = MagicMock()
        with patch("app.utils.dependencies.AuthService.decode_token", side_effect=Exception("bad")):
            user = get_optional_user(request, credentials)
            assert user is None

    def test_require_admin_user_admin_role(self):
        from app.utils.dependencies import require_admin_user

        user = MagicMock()
        user.role = "admin"
        user.app_metadata = {}
        result = require_admin_user(user=user)
        assert result is user

    def test_require_admin_user_non_admin(self):
        from fastapi import HTTPException

        from app.utils.dependencies import require_admin_user

        user = MagicMock()
        user.role = "user"
        user.app_metadata = {}
        with pytest.raises(HTTPException) as exc:
            require_admin_user(user=user)
        assert exc.value.status_code == 403

    def test_has_admin_scope_via_app_metadata_role(self):
        from app.utils.dependencies import _has_admin_scope

        user = MagicMock()
        user.role = "user"
        user.app_metadata = {"role": "admin"}
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_via_roles_list(self):
        from app.utils.dependencies import _has_admin_scope

        user = MagicMock()
        user.role = "user"
        user.app_metadata = {"roles": ["admin", "editor"]}
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_via_roles_str(self):
        from app.utils.dependencies import _has_admin_scope

        user = MagicMock()
        user.role = "user"
        user.app_metadata = {"roles": "admin"}
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_false(self):
        from app.utils.dependencies import _has_admin_scope

        user = MagicMock()
        user.role = "user"
        user.app_metadata = {}
        assert _has_admin_scope(user) is False

    def test_has_admin_scope_service_role(self):
        from app.utils.dependencies import _has_admin_scope

        user = MagicMock()
        user.role = "service_role"
        user.app_metadata = {}
        assert _has_admin_scope(user) is True

    def test_has_admin_scope_non_dict_metadata(self):
        from app.utils.dependencies import _has_admin_scope

        user = MagicMock()
        user.role = "user"
        user.app_metadata = None
        assert _has_admin_scope(user) is False
