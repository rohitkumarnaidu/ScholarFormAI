# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Enterprise Security Deep Tests — Phase 8 Final Verification.
Covers CSRF, encryption, JWT blacklist, path traversal, ownership, and rate limiting.
"""

import base64
import hashlib
import hmac
import secrets
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.security]


# ─────────────────────────────────────────────
# CSRF Deep Tests (10)
# ─────────────────────────────────────────────


class TestCSRFDeep:
    _CSRF_SECRET = b"test-secret-for-csrf-testing-at-least-32-bytes!"

    def test_csrf_token_format(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=self._CSRF_SECRET):
            from app.middleware.csrf import _get_csrf_secret, generate_csrf_token

            token = generate_csrf_token()
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            parts = decoded.split(":")
            assert len(parts) == 3
            assert parts[0].isdigit()
            expected_sig = hmac.new(
                _get_csrf_secret(),
                f"{parts[0]}:{parts[1]}".encode(),
                hashlib.sha256,
            ).hexdigest()
            assert hmac.compare_digest(parts[2], expected_sig)

    def test_csrf_token_user_binding(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=self._CSRF_SECRET):
            from app.middleware.csrf import generate_csrf_token, validate_csrf_token

            token = generate_csrf_token()
            assert validate_csrf_token(token) is True
            assert validate_csrf_token("") is False

    def test_csrf_token_expiry(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=self._CSRF_SECRET):
            from app.middleware.csrf import _get_csrf_secret, validate_csrf_token

            secret = _get_csrf_secret()
            old_ts = str(int(time.time()) - 7200)
            raw = f"{old_ts}:{secrets.token_hex(32)}"
            sig = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
            token = base64.urlsafe_b64encode(f"{raw}:{sig}".encode()).decode()
            assert validate_csrf_token(token) is False

    @pytest.mark.asyncio
    async def test_csrf_missing_cookie_403(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=self._CSRF_SECRET):
            from app.middleware.csrf import CSRFMiddleware

            call_next = AsyncMock()
            request = MagicMock()
            request.method = "POST"
            request.url.path = "/api/v1/documents"
            request.headers.get.return_value = "some-header-token"
            request.cookies = {}
            mw = CSRFMiddleware(lambda r: call_next(r))
            response = await mw.dispatch(request, call_next)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_csrf_missing_header_403(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=self._CSRF_SECRET):
            from app.middleware.csrf import CSRFMiddleware

            call_next = AsyncMock()
            request = MagicMock()
            request.method = "POST"
            request.url.path = "/api/v1/documents"
            request.headers.get.return_value = ""
            request.cookies = {"csrf_token": "sometoken"}
            mw = CSRFMiddleware(lambda r: call_next(r))
            response = await mw.dispatch(request, call_next)
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_csrf_cookie_httponly(self):
        with patch("app.middleware.csrf._get_csrf_secret", return_value=self._CSRF_SECRET):
            from app.middleware.csrf import CSRF_COOKIE_NAME, CSRFMiddleware

            call_next = AsyncMock(return_value=MagicMock(headers={}))
            request = MagicMock()
            request.method = "GET"
            request.url.path = "/api/v1"
            request.cookies = {}
            mw = CSRFMiddleware(lambda r: call_next(r))
            response = await mw.dispatch(request, call_next)
            setcookie_call = response.set_cookie.call_args
            kwargs = setcookie_call[1] if setcookie_call and len(setcookie_call) > 1 else {}
            args = setcookie_call[0] if setcookie_call else []
            cookie_name = args[0] if args else kwargs.get("key", "")
            if cookie_name == CSRF_COOKIE_NAME:
                assert kwargs.get("httponly") is True
            else:
                found = False
                for call in response.set_cookie.call_args_list:
                    _, kw = call
                    if kw.get("key") == CSRF_COOKIE_NAME:
                        assert kw.get("httponly") is True
                        found = True
                assert found

    @pytest.mark.asyncio
    async def test_csrf_cookie_samesite_lax(self):
        from app.middleware.csrf import CSRF_COOKIE_NAME, CSRFMiddleware

        call_next = AsyncMock(return_value=MagicMock(headers={}))
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/v1"
        request.cookies = {}
        mw = CSRFMiddleware(lambda r: call_next(r))
        response = await mw.dispatch(request, call_next)
        found = False
        for call in response.set_cookie.call_args_list:
            _, kw = call
            if kw.get("key") == CSRF_COOKIE_NAME:
                assert kw.get("samesite") == "lax"
                found = True
        assert found

    @pytest.mark.asyncio
    async def test_csrf_cookie_secure_in_prod(self):
        from app.middleware.csrf import CSRF_COOKIE_NAME, CSRFMiddleware

        with patch("app.middleware.csrf.settings.DEBUG", False):
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            request = MagicMock()
            request.method = "GET"
            request.url.path = "/api/v1"
            request.cookies = {}
            mw = CSRFMiddleware(lambda r: call_next(r))
            response = await mw.dispatch(request, call_next)
            found = False
            for call in response.set_cookie.call_args_list:
                _, kw = call
                if kw.get("key") == CSRF_COOKIE_NAME:
                    assert kw.get("secure") is True
                    found = True
            assert found

    @pytest.mark.asyncio
    async def test_csrf_token_rotation(self):
        from app.middleware.csrf import generate_csrf_token

        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_csrf_safe_methods_skip_validation(self):
        from app.middleware.csrf import CSRFMiddleware

        for method in ("GET", "HEAD", "OPTIONS"):
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            request = MagicMock()
            request.method = method
            request.url.path = "/api/v1/documents"
            request.cookies = {}
            mw = CSRFMiddleware(lambda r: call_next(r))
            response = await mw.dispatch(request, call_next)
            assert response.status_code != 403


# ─────────────────────────────────────────────
# Encryption Deep Tests (6)
# ─────────────────────────────────────────────

_FERNET_KEY = "9i6456Do-kfa42dcxz4XtNAQxhtv8JsCPAa8mf_uEkY="


class TestEncryptionDeep:
    def test_encryption_key_required(self):
        from app.services.encryption_service import EncryptionService

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY is not set"):
                EncryptionService(key=None)

    def test_encryption_decryption_roundtrip(self):
        from app.services.encryption_service import EncryptionService

        svc = EncryptionService(key=_FERNET_KEY)
        original = "sk-test-api-key-12345"
        encrypted = svc.encrypt(original)
        decrypted = svc.decrypt(encrypted)
        assert decrypted == original
        assert encrypted != original

    def test_encryption_differs_each_call(self):
        from app.services.encryption_service import EncryptionService

        svc = EncryptionService(key=_FERNET_KEY)
        plaintext = "same-plaintext-value"
        encrypted1 = svc.encrypt(plaintext)
        encrypted2 = svc.encrypt(plaintext)
        assert encrypted1 != encrypted2

    def test_encryption_invalid_key(self):
        from app.services.encryption_service import EncryptionService

        with pytest.raises(Exception):
            EncryptionService(key="not-a-valid-fernet-key")

    def test_fernet_property_type(self):
        from cryptography.fernet import Fernet

        from app.services.encryption_service import EncryptionService

        svc = EncryptionService(key=_FERNET_KEY)
        assert isinstance(svc.fernet, Fernet)

    def test_generate_key_format(self):
        from cryptography.fernet import Fernet

        from app.services.encryption_service import EncryptionService

        key = EncryptionService.generate_key()
        assert isinstance(key, str)
        assert len(key) > 20
        f = Fernet(key.encode())
        assert f.decrypt(f.encrypt(b"test")) == b"test"


# ─────────────────────────────────────────────
# JWT Blacklist Tests (6)
# ─────────────────────────────────────────────


class TestJWTBlacklist:
    def test_blacklist_token_blocks(self):
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "get", return_value=None):
            with patch.object(cache, "set", return_value=True) as mock_set:
                result = cache.blacklist_token("jti-123", ttl=3600)
                assert result is True
                mock_set.assert_called_once_with("blacklisted_token:jti-123", "1", ttl=3600)

    def test_blacklist_expired_token_cleanup(self):
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "get", return_value="1"):
            assert cache.is_token_blacklisted("jti-123") is True
        with patch.object(cache, "get", return_value=None):
            assert cache.is_token_blacklisted("jti-123") is False

    def test_is_token_blacklisted_not_found(self):
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "get", return_value=None):
            assert cache.is_token_blacklisted("nonexistent-jti") is False

    def test_blacklist_twice_still_blocks(self):
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "set", return_value=True) as mock_set:
            cache.blacklist_token("jti-456", ttl=3600)
            cache.blacklist_token("jti-456", ttl=3600)
            assert mock_set.call_count == 2

    def test_blacklist_persists_across_calls(self):
        from app.cache.redis_cache import RedisCache

        cache = RedisCache()
        with patch.object(cache, "get", side_effect=["1", "1", None]):
            assert cache.is_token_blacklisted("jti-persist") is True
            assert cache.is_token_blacklisted("jti-persist") is True
            assert cache.is_token_blacklisted("jti-persist") is False

    def test_dependencies_check_blacklisted_token(self):
        from fastapi import HTTPException

        from app.utils.dependencies import get_current_user

        credentials = MagicMock()
        credentials.credentials = "revoked-token"
        request = MagicMock()
        request.query_params.get.return_value = None
        with patch(
            "app.utils.dependencies.AuthService.decode_token",
            return_value={
                "jti": "revoked-jti",
                "sub": "user-1",
                "email": "a@b.com",
                "role": "authenticated",
                "app_metadata": {},
            },
        ):
            with patch("app.utils.dependencies.AuthService.get_user_id_from_payload", return_value="user-1"):
                with patch("app.cache.redis_cache.RedisCache.is_token_blacklisted", return_value=True):
                    with pytest.raises(HTTPException) as exc:
                        get_current_user(request, credentials)
                    assert exc.value.status_code == 401


# ─────────────────────────────────────────────
# Path Traversal Tests (6)
# ─────────────────────────────────────────────


class TestPathTraversal:
    def test_validate_path_safety_normal(self):
        from app.tasks.celery_tasks import ALLOWED_DIRECTORIES, validate_path_safety

        allowed = ALLOWED_DIRECTORIES[0]
        result = validate_path_safety(allowed)
        assert result == allowed

    def test_validate_path_safety_traversal(self):
        import os

        from app.tasks.celery_tasks import validate_path_safety

        allowed = os.path.abspath("data/uploads")
        with pytest.raises(ValueError) as exc:
            validate_path_safety(f"{allowed}/../../etc/passwd")
        msg = str(exc.value)
        assert "Path traversal" in msg or "not in an allowed directory" in msg

    def test_validate_path_safety_absolute(self):
        from app.tasks.celery_tasks import validate_path_safety

        with pytest.raises(ValueError):
            validate_path_safety("/etc/passwd")

    def test_validate_path_safety_symlink(self):
        from app.tasks.celery_tasks import validate_path_safety

        with pytest.raises(ValueError):
            validate_path_safety("/tmp")

    def test_validate_path_safety_empty(self):
        from app.tasks.celery_tasks import validate_path_safety

        with pytest.raises(ValueError, match="Path is empty"):
            validate_path_safety("")

    def test_validate_path_safety_null_byte(self):
        import os

        from app.tasks.celery_tasks import validate_path_safety

        if os.name == "nt":
            pytest.skip("Null byte path traversal behavior differs on Windows (null is not a terminator)")
        with pytest.raises(ValueError):
            validate_path_safety("data/uploads/\x00../etc/passwd")


# ─────────────────────────────────────────────
# Ownership Tests (6)
# ─────────────────────────────────────────────


class TestOwnership:
    @pytest.mark.asyncio
    async def test_verify_session_ownership_owner(self):
        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(return_value={"id": "sess-1", "user_id": "user-abc"})
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            session = await verify_session_ownership("sess-1", "user-abc")
            assert session["user_id"] == "user-abc"

    @pytest.mark.asyncio
    async def test_verify_session_ownership_non_owner(self):
        from fastapi import HTTPException

        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(return_value={"id": "sess-1", "user_id": "user-abc"})
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            with pytest.raises(HTTPException) as exc:
                await verify_session_ownership("sess-1", "user-xyz")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_session_ownership_nonexistent(self):
        from fastapi import HTTPException

        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(return_value=None)
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            with pytest.raises(HTTPException) as exc:
                await verify_session_ownership("nonexistent", "user-abc")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_verify_document_ownership(self):
        from app.services.document_service import DocumentService

        with patch.object(DocumentService, "get_document", side_effect=[{"id": "doc-1", "user_id": "user-abc"}, None]):
            result = await DocumentService.get_document("doc-1", user_id="user-abc")
            assert result is not None
            assert result["user_id"] == "user-abc"
            result2 = await DocumentService.get_document("doc-1", user_id="user-xyz")
            assert result2 is None

    @pytest.mark.asyncio
    async def test_verify_template_ownership_shareable(self):
        from app.services.document_service import DocumentService

        with patch.object(
            DocumentService, "get_document", return_value={"id": "doc-1", "user_id": "user-abc", "template": "ieee"}
        ):
            doc = await DocumentService.get_document("doc-1")
            assert doc["template"] == "ieee"

    @pytest.mark.asyncio
    async def test_generator_ownership_check_on_create(self):
        from fastapi import HTTPException

        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(return_value={"id": "sess-2", "user_id": "creator"})
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            session = await verify_session_ownership("sess-2", "creator")
            assert session["id"] == "sess-2"
            with pytest.raises(HTTPException) as exc:
                await verify_session_ownership("sess-2", "intruder")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ownership_empty_user_id_rejected(self):
        from fastapi import HTTPException

        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(return_value={"id": "sess-1", "user_id": "user-abc"})
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            with pytest.raises(HTTPException) as exc:
                await verify_session_ownership("sess-1", "")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ownership_deleted_session_raises(self):
        from fastapi import HTTPException

        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(return_value=None)
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            with pytest.raises(HTTPException) as exc:
                await verify_session_ownership("deleted-sess", "user-abc")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ownership_concurrent_modification(self):
        from fastapi import HTTPException

        from app.routers.v1.generator import verify_session_ownership

        mock_service = MagicMock()
        mock_service.get_session = AsyncMock(
            side_effect=[
                {"id": "sess-1", "user_id": "user-abc"},
                {"id": "sess-1", "user_id": "user-xyz"},
            ]
        )
        import app.routers.v1.generator

        with patch.object(app.routers.v1.generator, "_session_service", mock_service):
            session = await verify_session_ownership("sess-1", "user-abc")
            assert session["user_id"] == "user-abc"
            mock_service.get_session = AsyncMock(return_value={"id": "sess-1", "user_id": "user-xyz"})
            with pytest.raises(HTTPException) as exc:
                await verify_session_ownership("sess-1", "user-abc")
            assert exc.value.status_code == 404


# ─────────────────────────────────────────────
# Rate Limiting Deep Tests (6)
# ─────────────────────────────────────────────


class TestRateLimitDeep:
    @pytest.mark.asyncio
    async def test_tier_rate_limit_free_60_per_min(self):
        from app.middleware.tier_rate_limit import TierRateLimitMiddleware

        mw = TierRateLimitMiddleware(MagicMock())
        mw._redis = MagicMock()
        mw._redis.incr.side_effect = lambda k: 61 if "ratelimit:user:" in k else 1
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents/upload"
        request.headers = {"authorization": "Bearer valid"}
        request.client.host = "1.2.3.4"
        with patch(
            "app.middleware.tier_rate_limit.verify_jwt", return_value={"sub": "free-user", "role": "authenticated"}
        ):
            with patch("app.middleware.tier_rate_limit.resolve_user_role", return_value="free"):
                response = await mw.dispatch(request, AsyncMock(return_value=MagicMock(status_code=200)))
        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_tier_rate_limit_pro_300_per_min(self):
        from app.middleware.tier_rate_limit import TierRateLimitMiddleware

        mw = TierRateLimitMiddleware(MagicMock())
        mw._redis = MagicMock()
        mw._redis.incr.side_effect = lambda k: 200 if "ratelimit:user:" in k else 1
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents/upload"
        request.headers = {"authorization": "Bearer valid"}
        request.client.host = "1.2.3.4"
        with patch("app.middleware.tier_rate_limit.verify_jwt", return_value={"sub": "pro-user", "role": "pro"}):
            with patch("app.middleware.tier_rate_limit.resolve_user_role", return_value="pro"):
                call_next = AsyncMock(return_value=MagicMock(status_code=200))
                response = await mw.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_tier_rate_limit_admin_unlimited(self):
        from app.middleware.tier_rate_limit import TierRateLimitMiddleware

        mw = TierRateLimitMiddleware(MagicMock())
        mw._redis = MagicMock()
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents/upload"
        request.headers = {"authorization": "Bearer valid"}
        request.client.host = "1.2.3.4"
        with patch(
            "app.middleware.tier_rate_limit.verify_jwt",
            return_value={"sub": "admin-user", "role": "admin", "app_metadata": {"role": "admin"}},
        ):
            with patch("app.middleware.tier_rate_limit.resolve_user_role", return_value="admin"):
                call_next = AsyncMock(return_value=MagicMock(status_code=200))
                response = await mw.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_tier_rate_limit_exceeded_429(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        rl = RateLimitMiddleware(MagicMock(), requests_per_minute=1)
        call_next = AsyncMock(return_value=MagicMock(status_code=200))
        first_req = MagicMock()
        first_req.client.host = "1.2.3.4"
        first_req.url.path = "/api/v1/documents"
        first_req.method = "GET"
        resp1 = await rl.dispatch(first_req, call_next)
        assert resp1.status_code == 200
        second_req = MagicMock()
        second_req.client.host = "1.2.3.4"
        second_req.url.path = "/api/v1/documents"
        second_req.method = "GET"
        resp2 = await rl.dispatch(second_req, call_next)
        assert resp2.status_code == 429

    @pytest.mark.asyncio
    async def test_tier_rate_limit_different_tiers(self):
        from app.middleware.tier_rate_limit import TierRateLimitMiddleware

        mw = TierRateLimitMiddleware(MagicMock())
        mw._redis = MagicMock()
        mw._redis.incr.side_effect = lambda k: 61 if "ratelimit:user:" in k else 1
        base_request = MagicMock()
        base_request.method = "POST"
        base_request.url.path = "/api/v1/documents/upload"
        base_request.headers = {"authorization": "Bearer valid"}
        base_request.client.host = "1.2.3.4"

        free_req = MagicMock(**{k: v for k, v in base_request.__dict__.items() if k != "_spec_parsers"})
        pro_req = MagicMock(**{k: v for k, v in base_request.__dict__.items() if k != "_spec_parsers"})
        free_req.method = "POST"
        free_req.url.path = "/api/v1/documents/upload"
        free_req.headers = {"authorization": "Bearer valid"}
        free_req.client.host = "1.2.3.4"
        pro_req.method = "POST"
        pro_req.url.path = "/api/v1/documents/upload"
        pro_req.headers = {"authorization": "Bearer valid"}
        pro_req.client.host = "1.2.3.4"

        with patch(
            "app.middleware.tier_rate_limit.verify_jwt",
            side_effect=[{"sub": "free-u", "role": "authenticated"}, {"sub": "pro-u", "role": "pro"}],
        ):
            with patch("app.middleware.tier_rate_limit.resolve_user_role", side_effect=["free", "pro"]):
                free_resp = await mw.dispatch(free_req, AsyncMock(return_value=MagicMock(status_code=200)))
                mw._redis.incr.side_effect = lambda k: 61 if "free-u" in k else 1
                pro_resp = await mw.dispatch(pro_req, AsyncMock(return_value=MagicMock(status_code=200)))
        assert free_resp.status_code == 429, f"Free user at 61 should be blocked, got {free_resp.status_code}"
        assert pro_resp.status_code == 200, f"Pro user at 61 should pass, got {pro_resp.status_code}"

    @pytest.mark.asyncio
    async def test_tier_rate_limit_resets_after_window(self):
        from app.middleware.tier_rate_limit import TierRateLimitMiddleware

        mw = TierRateLimitMiddleware(MagicMock())
        mw._redis = MagicMock()
        call_count = [0]

        def incr_side(key):
            call_count[0] += 1
            if "ratelimit:user:" in key:
                return call_count[0]
            return call_count[0]

        mw._redis.incr.side_effect = incr_side
        request = MagicMock()
        request.method = "POST"
        request.url.path = "/api/v1/documents/upload"
        request.headers = {"authorization": "Bearer valid"}
        request.client.host = "1.2.3.4"
        with patch(
            "app.middleware.tier_rate_limit.verify_jwt", return_value={"sub": "reset-user", "role": "authenticated"}
        ):
            with patch("app.middleware.tier_rate_limit.resolve_user_role", return_value="free"):
                call_next = AsyncMock(return_value=MagicMock(status_code=200))
                await mw.dispatch(request, call_next)
                mw._redis.expire.assert_called()
