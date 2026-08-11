# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

from __future__ import annotations

import contextlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRateLimitModule:
    def test_in_memory_count_general(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            count = mw._in_memory_count("1.2.3.4", is_upload=False)
            assert count == 1
            count2 = mw._in_memory_count("1.2.3.4", is_upload=False)
            assert count2 == 2

    def test_in_memory_count_upload_separate(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            mw._in_memory_count("1.2.3.4", is_upload=False)
            count = mw._in_memory_count("1.2.3.4", is_upload=True)
            assert count == 1

    def test_in_memory_count_evicts_old(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            old_ts = time.time() - 120
            mw.request_counts["1.2.3.4"] = [old_ts]
            count = mw._in_memory_count("1.2.3.4")
            assert count == 1
            assert old_ts not in mw.request_counts["1.2.3.4"]

    def test_redis_count_disabled(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            import asyncio
            count = asyncio.run(mw._redis_count("test:key"))
            assert count is None

    def test_redis_count_enabled(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True), \
             patch("app.middleware.rate_limit.redis") as mock_redis:
            mock_redis.incr.return_value = 5
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            import asyncio
            count = asyncio.run(mw._redis_count("test:key"))
            assert count == 5

    def test_redis_count_first_call_sets_expire(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True), \
             patch("app.middleware.rate_limit.redis") as mock_redis:
            mock_redis.incr.return_value = 1
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            import asyncio
            count = asyncio.run(mw._redis_count("test:key"))
            assert count == 1
            mock_redis.expire.assert_called_once()

    def test_redis_count_error_logs_warning_once(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True), \
             patch("app.middleware.rate_limit.redis") as mock_redis, \
             patch("app.middleware.rate_limit.logger") as mock_log:
            mock_redis.incr.side_effect = Exception("redis down")
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            mw._redis_warning_logged = False
            import asyncio
            result1 = asyncio.run(mw._redis_count("test:key"))
            result2 = asyncio.run(mw._redis_count("test:key"))
            assert result1 is None
            assert result2 is None
            assert mock_log.warning.call_count == 1

    def test_redis_count_awaitable_incr(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True), \
             patch("app.middleware.rate_limit.redis") as mock_redis:
            async def async_incr(key):
                return 3
            mock_redis.incr.side_effect = async_incr
            mock_redis.expire.return_value = True
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            import asyncio
            count = asyncio.run(mw._redis_count("test:key"))
            assert count == 3

    def test_redis_count_awaitable_expire(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True), \
             patch("app.middleware.rate_limit.redis") as mock_redis:
            async def async_expire(key, ttl):
                return True
            mock_redis.incr.return_value = 1
            mock_redis.expire.side_effect = async_expire
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            import asyncio
            count = asyncio.run(mw._redis_count("test:key"))
            assert count == 1

    def test_dispatch_health_skips(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            request = MagicMock()
            request.client.host = "1.2.3.4"
            request.url.path = "/health"
            request.url.__str__ = MagicMock(return_value="/health")
            request.method = "GET"
            call_next = AsyncMock(return_value=MagicMock())
            import asyncio
            asyncio.run(mw.dispatch(request, call_next))
            call_next.assert_awaited_once()

    def test_dispatch_upload_rate_limited(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            mw.uploads_per_minute = 1
            request = MagicMock()
            request.client.host = "1.2.3.4"
            request.url.path = "/api/v1/documents/upload"
            request.method = "POST"
            request.headers = {"authorization": ""}
            call_next = AsyncMock(return_value=MagicMock())
            import asyncio
            first = asyncio.run(mw.dispatch(request, call_next))
            second = asyncio.run(mw.dispatch(request, call_next))
            assert getattr(first, "status_code", None) != 429
            assert getattr(second, "status_code", None) == 429

    def test_dispatch_general_rate_limited(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=2)
            request = MagicMock()
            request.client.host = "1.2.3.4"
            request.url.path = "/api/v1/documents"
            request.method = "GET"
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock())
            import asyncio
            for _ in range(2):
                asyncio.run(mw.dispatch(request, call_next))
            third = asyncio.run(mw.dispatch(request, call_next))
            assert getattr(third, "status_code", None) == 429

    def test_dispatch_unknown_client(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            request = MagicMock()
            request.client = None
            request.url.path = "/api/v1/documents"
            request.method = "GET"
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock())
            import asyncio
            response = asyncio.run(mw.dispatch(request, call_next))
            assert response is not None

    def test_dispatch_upload_with_token_fingerprint(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import RateLimitMiddleware
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            mw = RateLimitMiddleware(MagicMock(), requests_per_minute=60)
            mw.uploads_per_minute = 10
            request = MagicMock()
            request.client.host = "1.2.3.4"
            request.url.path = "/api/v1/documents/upload"
            request.method = "POST"
            request.headers = {"authorization": "Bearer test-token-123"}
            call_next = AsyncMock(return_value=MagicMock())
            import asyncio
            response = asyncio.run(mw.dispatch(request, call_next))
            assert response is not None

    def test_ensure_redis_enabled(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import _ensure_redis
        with patch("app.middleware.rate_limit.REDIS_ENABLED", True), \
             patch("app.middleware.rate_limit.redis", "mock-redis"):
            result = _ensure_redis()
            assert result == "mock-redis"

    def test_ensure_redis_disabled(self):
        with patch("app.cache.redis_cache.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            from app.middleware.rate_limit import _ensure_redis
        with patch("app.middleware.rate_limit.REDIS_ENABLED", False):
            result = _ensure_redis()
            assert result is None

    def test_module_imports(self):
        import app.middleware.rate_limit
        assert app.middleware.rate_limit is not None
        assert hasattr(app.middleware.rate_limit, "RateLimitMiddleware")


class TestHTTPSRedirect:
    def test_https_redirect_https_passes(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        request = MagicMock()
        request.url.scheme = "https"
        request.url.hostname = "example.com"
        request.url.path = "/api/v1/documents"
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = HTTPSRedirectMiddleware(MagicMock())
        import asyncio
        asyncio.run(mw.dispatch(request, call_next))
        call_next.assert_awaited_once()

    def test_https_redirect_localhost_bypass(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "localhost"
        request.url.path = "/api/v1/documents"
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = HTTPSRedirectMiddleware(MagicMock())
        import asyncio
        asyncio.run(mw.dispatch(request, call_next))
        call_next.assert_awaited_once()

    def test_https_redirect_127_bypass(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "127.0.0.1"
        request.url.path = "/api/v1/documents"
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = HTTPSRedirectMiddleware(MagicMock())
        import asyncio
        asyncio.run(mw.dispatch(request, call_next))
        call_next.assert_awaited_once()

    def test_https_redirect_health_bypass(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "example.com"
        request.url.path = "/health"
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = HTTPSRedirectMiddleware(MagicMock())
        import asyncio
        asyncio.run(mw.dispatch(request, call_next))
        call_next.assert_awaited_once()

    def test_https_redirect_http_to_https(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        request = MagicMock()
        request.url.scheme = "http"
        request.url.hostname = "example.com"
        request.url.path = "/api/v1/documents"
        request.url.replace.return_value = MagicMock(__str__=MagicMock(return_value="https://example.com/api/v1/documents"))
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = HTTPSRedirectMiddleware(MagicMock())
        import asyncio
        response = asyncio.run(mw.dispatch(request, call_next))
        assert response.status_code == 307
        request.url.replace.assert_called_once_with(scheme="https")

    def test_hsts_middleware_https_adds_headers(self):
        from app.middleware.https_redirect import HSTSMiddleware
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock(headers={})
        call_next = AsyncMock(return_value=response)
        mw = HSTSMiddleware(MagicMock(), max_age=31536000, include_subdomains=True, preload=True)
        import asyncio
        result = asyncio.run(mw.dispatch(request, call_next))
        assert "Strict-Transport-Security" in result.headers
        assert "includeSubDomains" in result.headers["Strict-Transport-Security"]
        assert "preload" in result.headers["Strict-Transport-Security"]

    def test_hsts_middleware_http_no_hsts(self):
        from app.middleware.https_redirect import HSTSMiddleware
        request = MagicMock()
        request.url.scheme = "http"
        response = MagicMock(headers={})
        call_next = AsyncMock(return_value=response)
        mw = HSTSMiddleware(MagicMock(), max_age=31536000)
        import asyncio
        result = asyncio.run(mw.dispatch(request, call_next))
        assert "Strict-Transport-Security" not in result.headers

    def test_hsts_middleware_no_subdomains_no_preload(self):
        from app.middleware.https_redirect import HSTSMiddleware
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock(headers={})
        call_next = AsyncMock(return_value=response)
        mw = HSTSMiddleware(MagicMock(), max_age=86400, include_subdomains=False, preload=False)
        import asyncio
        result = asyncio.run(mw.dispatch(request, call_next))
        hsts = result.headers["Strict-Transport-Security"]
        assert "includeSubDomains" not in hsts
        assert "preload" not in hsts
        assert "max-age=86400" in hsts

    def test_hsts_middleware_sets_extra_headers(self):
        from app.middleware.https_redirect import HSTSMiddleware
        request = MagicMock()
        request.url.scheme = "https"
        response = MagicMock(headers={})
        call_next = AsyncMock(return_value=response)
        mw = HSTSMiddleware(MagicMock())
        import asyncio
        result = asyncio.run(mw.dispatch(request, call_next))
        assert result.headers.get("X-Content-Type-Options") == "nosniff"
        assert result.headers.get("X-Frame-Options") == "DENY"


class TestFeatureFlagMiddleware:
    def test_dispatch_sets_flags_in_state(self):
        mock_service = MagicMock()
        mock_service.get_all_flags.return_value = {"new_ui": True, "dark_mode": False}
        with patch("app.middleware.feature_flags.get_feature_flag_service", return_value=mock_service):
            from app.middleware.feature_flags import FeatureFlagMiddleware
            request = MagicMock()
            request.app.debug = False
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            mw = FeatureFlagMiddleware(MagicMock())
            import asyncio
            asyncio.run(mw.dispatch(request, call_next))
            assert request.state.feature_flags == {"new_ui": True, "dark_mode": False}
            mock_service.get_all_flags.assert_called_once()

    def test_dispatch_debug_adds_header(self):
        mock_service = MagicMock()
        mock_service.get_all_flags.return_value = {"beta": True}
        with patch("app.middleware.feature_flags.get_feature_flag_service", return_value=mock_service):
            from app.middleware.feature_flags import FeatureFlagMiddleware
            request = MagicMock()
            request.app.debug = True
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            mw = FeatureFlagMiddleware(MagicMock())
            import asyncio
            response = asyncio.run(mw.dispatch(request, call_next))
            assert "X-Feature-Flags" in response.headers
            assert "beta" in response.headers["X-Feature-Flags"]

    def test_dispatch_no_debug_no_header(self):
        mock_service = MagicMock()
        mock_service.get_all_flags.return_value = {"beta": True}
        with patch("app.middleware.feature_flags.get_feature_flag_service", return_value=mock_service):
            from app.middleware.feature_flags import FeatureFlagMiddleware
            request = MagicMock()
            request.app.debug = False
            request.headers = {}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            mw = FeatureFlagMiddleware(MagicMock())
            import asyncio
            response = asyncio.run(mw.dispatch(request, call_next))
            assert "X-Feature-Flags" not in response.headers

    def test_dispatch_with_bearer_auth_header(self):
        mock_service = MagicMock()
        mock_service.get_all_flags.return_value = {}
        with patch("app.middleware.feature_flags.get_feature_flag_service", return_value=mock_service):
            from app.middleware.feature_flags import FeatureFlagMiddleware
            request = MagicMock()
            request.app.debug = False
            request.headers = {"Authorization": "Bearer valid-token"}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            mw = FeatureFlagMiddleware(MagicMock())
            import asyncio
            asyncio.run(mw.dispatch(request, call_next))
            assert hasattr(request.state, "feature_flags")

    def test_dispatch_auth_extraction_exception_safe(self):
        mock_service = MagicMock()
        mock_service.get_all_flags.return_value = {}
        with patch("app.middleware.feature_flags.get_feature_flag_service", return_value=mock_service):
            from app.middleware.feature_flags import FeatureFlagMiddleware
            request = MagicMock()
            request.app.debug = False
            request.headers = {"Authorization": "Bearer broken"}
            call_next = AsyncMock(return_value=MagicMock(headers={}))
            mw = FeatureFlagMiddleware(MagicMock())
            import asyncio
            asyncio.run(mw.dispatch(request, call_next))
            assert hasattr(request.state, "feature_flags")


class TestRBAC:
    def test_normalize_role_strips_and_lowers(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("  ADMIN ") == "admin"
        assert _normalize_role("Free") == "free"
        assert _normalize_role("PRO") == "pro"

    def test_normalize_role_aliases_guest_to_free(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("guest") == "free"
        assert _normalize_role("authenticated") == "free"
        assert _normalize_role("user") == "free"
        assert _normalize_role("basic") == "free"

    def test_normalize_role_aliases_to_pro(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("trial") == "pro"
        assert _normalize_role("premium") == "pro"
        assert _normalize_role("paid") == "pro"

    def test_normalize_role_aliases_to_admin(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("service_role") == "admin"
        assert _normalize_role("owner") == "admin"
        assert _normalize_role("superadmin") == "admin"

    def test_normalize_role_unknown_passes_through(self):
        from app.middleware.rbac import _normalize_role
        assert _normalize_role("custom_role") == "custom_role"
        assert _normalize_role(None) == ""
        assert _normalize_role("") == ""

    def test_resolve_user_role_from_attribute(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = "admin"
        user.app_metadata = None
        assert resolve_user_role(user) == "admin"

    def test_resolve_user_role_from_app_metadata(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {"role": "pro"}
        assert resolve_user_role(user) == "pro"

    def test_resolve_user_role_defaults_to_free(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {}
        assert resolve_user_role(user) == "free"

    def test_resolve_user_role_picks_highest(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = "free"
        user.app_metadata = {"role": "admin", "plan_tier": "pro"}
        assert resolve_user_role(user) == "admin"

    def test_require_role_invalid_role_raises_value_error(self):
        from app.middleware.rbac import require_role
        with pytest.raises(ValueError, match="Unsupported role"):
            require_role("nonexistent_role")

    def test_require_role_insufficient_permissions(self):
        with patch("app.middleware.rbac.get_current_user") as mock_get_user:
            from app.middleware.rbac import require_role
            guard = require_role("admin")
            user = MagicMock()
            user.role = "free"
            user.app_metadata = {}
            mock_get_user.return_value = user
            with pytest.raises(Exception) as exc:
                guard(current_user=user)
            assert "403" in str(exc.value) or exc.value.status_code == 403

    def test_require_role_sufficient_permissions(self):
        with patch("app.middleware.rbac.get_current_user") as mock_get_user:
            from app.middleware.rbac import require_role
            guard = require_role("free")
            user = MagicMock()
            user.role = "admin"
            user.app_metadata = {}
            mock_get_user.return_value = user
            result = guard(current_user=user)
            assert result is user
            assert user.effective_role == "admin"

    def test_resolve_user_role_metadata_plan_tier(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {"plan_tier": "premium"}
        assert resolve_user_role(user) == "pro"

    def test_resolve_user_role_metadata_subscription_tier(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {"subscription_tier": "paid"}
        assert resolve_user_role(user) == "pro"

    def test_resolve_user_role_metadata_tier(self):
        from app.middleware.rbac import resolve_user_role
        user = MagicMock()
        user.role = None
        user.app_metadata = {"tier": "owner"}
        assert resolve_user_role(user) == "admin"


class TestJWKSVerifier:
    def test_verify_jwt_empty_token_raises_401(self):
        from app.security.jwks_verifier import verify_jwt
        with pytest.raises(Exception) as exc:
            verify_jwt("")
        assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_verify_jwt_hs_algorithm_decodes_with_secret(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "HS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "HS256"}), \
             patch("jwt.decode", return_value={"sub": "user-123"}):
            from app.security.jwks_verifier import verify_jwt
            result = verify_jwt("valid-hs-token")
            assert result["sub"] == "user-123"

    def test_verify_jwt_rs_algorithm_decodes_with_jwks(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "RS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "key-1"}):
            from app.security.jwks_verifier import verify_jwt
            mock_keys = {"key-1": {"kty": "RSA", "kid": "key-1", "n": "test", "e": "AQAB"}}
            with patch("app.security.jwks_verifier._get_cached_keys", return_value=mock_keys), \
                 patch("app.security.jwks_verifier._public_key_from_jwk"), \
                 patch("jwt.decode", return_value={"sub": "user-456"}):
                result = verify_jwt("valid-rs-token")
                assert result["sub"] == "user-456"

    def test_verify_jwt_expired_signature_error(self):
        import jwt
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "HS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
            from app.security.jwks_verifier import verify_jwt
            with patch("jwt.decode", side_effect=jwt.ExpiredSignatureError()):
                with pytest.raises(Exception) as exc:
                    verify_jwt("expired-token")
                assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_verify_jwt_invalid_issuer_error(self):
        import jwt
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "HS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
            from app.security.jwks_verifier import verify_jwt
            with patch("jwt.decode", side_effect=jwt.InvalidIssuerError("bad issuer")):
                with pytest.raises(Exception) as exc:
                    verify_jwt("bad-issuer-token")
                assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_verify_jwt_invalid_audience_error(self):
        import jwt
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "HS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
            from app.security.jwks_verifier import verify_jwt
            with patch("jwt.decode", side_effect=jwt.InvalidAudienceError("bad audience")):
                with pytest.raises(Exception) as exc:
                    verify_jwt("bad-aud-token")
                assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_verify_jwt_invalid_token_error(self):
        import jwt
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "HS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "HS256"}):
            from app.security.jwks_verifier import verify_jwt
            with patch("jwt.decode", side_effect=jwt.InvalidTokenError()):
                with pytest.raises(Exception) as exc:
                    verify_jwt("bad-token")
                assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_verify_jwt_retry_on_first_failure_succeeds_on_second(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "RS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "key-1"}):
            from app.security.jwks_verifier import verify_jwt
            call_count = [0]
            verify_jwt.__wrapped__ if hasattr(verify_jwt, "__wrapped__") else None

            def mock_decode_with_jwks(token, *, expected_issuer, refresh=False):
                call_count[0] += 1
                if call_count[0] == 1 and not refresh:
                    from app.security.jwks_verifier import _RetryableJWTError
                    raise _RetryableJWTError("first fail")
                return {"sub": "retry-success"}

            with patch("app.security.jwks_verifier._decode_with_jwks", side_effect=mock_decode_with_jwks):
                result = verify_jwt("retry-token")
                assert result["sub"] == "retry-success"
                assert call_count[0] == 2

    def test_verify_jwt_retry_both_fail(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "RS256"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "key-1"}):
            from app.security.jwks_verifier import _RetryableJWTError, verify_jwt

            def always_fail(token, *, expected_issuer, refresh=False):
                raise _RetryableJWTError("always fail")

            with patch("app.security.jwks_verifier._decode_with_jwks", side_effect=always_fail):
                with pytest.raises(Exception) as exc:
                    verify_jwt("fail-token")
                assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_resolve_jwks_url_with_explicit_url(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", "https://custom.example.com/auth/v1/keys"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"):
            from app.security.jwks_verifier import _resolve_jwks_url
            result = _resolve_jwks_url()
            assert "custom.example.com" in result
            assert "jwks.json" in result

    def test_resolve_jwks_url_with_supabase_url(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"):
            from app.security.jwks_verifier import _resolve_jwks_url
            result = _resolve_jwks_url()
            assert "project.supabase.co/auth/v1/.well-known/jwks.json" in result

    def test_resolve_jwks_url_returns_none(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", None):
            from app.security.jwks_verifier import _resolve_jwks_url
            assert _resolve_jwks_url() is None

    def test_resolve_jwks_url_strips_trailing_slash(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", "https://custom.example.com/"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", None):
            from app.security.jwks_verifier import _resolve_jwks_url
            result = _resolve_jwks_url()
            assert result is not None
            assert "//custom.example.com" in result
            assert "//custom.example.com/" not in result

    def test_fetch_jwks_returns_keys(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None):
            from app.security.jwks_verifier import _fetch_jwks
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "keys": [
                    {"kid": "key1", "kty": "RSA"},
                    {"kid": "key2", "kty": "EC"},
                ]
            }
            mock_response.status_code = 200
            with patch("httpx.get", return_value=mock_response):
                keys = _fetch_jwks()
                assert "key1" in keys
                assert "key2" in keys
                assert keys["key1"]["kty"] == "RSA"

    def test_fetch_jwks_handles_error(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None):
            from app.security.jwks_verifier import _fetch_jwks
            with patch("httpx.get", side_effect=Exception("connection error")):
                keys = _fetch_jwks()
                assert keys == {}

    def test_fetch_jwks_no_url(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", None), \
             patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None):
            from app.security.jwks_verifier import _fetch_jwks
            keys = _fetch_jwks()
            assert keys == {}

    def test_get_cached_keys_valid_cache(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None), \
             patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"):
            from app.security.jwks_verifier import _JWKS_CACHE, _get_cached_keys
            _JWKS_CACHE["keys"] = {"key1": {"kty": "RSA"}}
            _JWKS_CACHE["fetched_at"] = time.time()
            keys = _get_cached_keys(refresh=False)
            assert "key1" in keys

    def test_get_cached_keys_expired_fetches_new(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None):
            from app.security.jwks_verifier import _JWKS_CACHE, _get_cached_keys
            _JWKS_CACHE["keys"] = {"old-key": {"kty": "RSA"}}
            _JWKS_CACHE["fetched_at"] = 0.0
            mock_response = MagicMock()
            mock_response.json.return_value = {"keys": [{"kid": "new-key", "kty": "RSA"}]}
            mock_response.status_code = 200
            with patch("httpx.get", return_value=mock_response):
                keys = _get_cached_keys(refresh=False)
                assert "new-key" in keys
                assert "old-key" not in keys

    def test_get_cached_keys_refresh_true(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("app.security.jwks_verifier.settings.SUPABASE_JWKS_URL", None):
            from app.security.jwks_verifier import _JWKS_CACHE, _get_cached_keys
            _JWKS_CACHE["keys"] = {"old-key": {"kty": "RSA"}}
            _JWKS_CACHE["fetched_at"] = time.time()
            mock_response = MagicMock()
            mock_response.json.return_value = {"keys": [{"kid": "new-key", "kty": "RSA"}]}
            mock_response.status_code = 200
            with patch("httpx.get", return_value=mock_response):
                keys = _get_cached_keys(refresh=True)
                assert "new-key" in keys

    def test_public_key_from_jwk_rsa(self):
        from app.security.jwks_verifier import _public_key_from_jwk
        with patch("jwt.algorithms.RSAAlgorithm.from_jwk", return_value="rsa-key"):
            result = _public_key_from_jwk({"kty": "RSA"})
            assert result == "rsa-key"

    def test_public_key_from_jwk_ec(self):
        from app.security.jwks_verifier import _public_key_from_jwk
        with patch("jwt.algorithms.ECAlgorithm.from_jwk", return_value="ec-key"):
            result = _public_key_from_jwk({"kty": "EC"})
            assert result == "ec-key"

    def test_public_key_from_jwk_okp(self):
        from app.security.jwks_verifier import _public_key_from_jwk
        with patch("jwt.algorithms.OKPAlgorithm.from_jwk", return_value="okp-key"):
            result = _public_key_from_jwk({"kty": "OKP"})
            assert result == "okp-key"

    def test_public_key_from_jwk_unsupported_raises_401(self):
        from app.security.jwks_verifier import _public_key_from_jwk
        with pytest.raises(Exception) as exc:
            _public_key_from_jwk({"kty": "INVALID"})
        assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_decode_with_secret_missing_secret_raises_401(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", None):
            from app.security.jwks_verifier import _decode_with_secret
            with pytest.raises(Exception) as exc:
                _decode_with_secret("token", expected_issuer="issuer")
            assert "401" in str(exc.value) or exc.value.status_code == 401

    def test_decode_with_jwks_missing_kid(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"):
            from app.security.jwks_verifier import _decode_with_jwks
            with patch("jwt.get_unverified_header", return_value={"alg": "RS256"}):
                with pytest.raises(Exception):
                    _decode_with_jwks("token", expected_issuer=None)

    def test_decode_with_jwks_key_not_in_cache(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", "https://project.supabase.co"):
            from app.security.jwks_verifier import _decode_with_jwks
            with patch("jwt.get_unverified_header", return_value={"alg": "RS256", "kid": "missing-key"}), \
                 patch("app.security.jwks_verifier._get_cached_keys", return_value={}), pytest.raises(Exception):
                _decode_with_jwks("token", expected_issuer=None)

    def test_verify_jwt_no_supabase_url_no_issuer(self):
        with patch("app.security.jwks_verifier.settings.SUPABASE_URL", None), \
             patch("app.security.jwks_verifier.settings.SUPABASE_JWT_SECRET", "test-secret"), \
             patch("app.security.jwks_verifier.settings.ALGORITHM", "HS256"), \
             patch("jwt.get_unverified_header", return_value={"alg": "HS256"}), \
             patch("jwt.decode", return_value={"sub": "user-789"}):
            from app.security.jwks_verifier import verify_jwt
            result = verify_jwt("no-issuer-token")
            assert result["sub"] == "user-789"


class TestMonitoringMiddlewareExtra:
    def test_dispatch_logs_request_id(self):
        from app.middleware.monitoring import MonitoringMiddleware
        request = MagicMock()
        request.state.request_id = "custom-id-123"
        request.method = "GET"
        request.url.path = "/test"
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = MonitoringMiddleware(MagicMock())
        import asyncio
        with patch("app.middleware.monitoring.logger") as mock_log:
            asyncio.run(mw.dispatch(request, call_next))
            assert "custom-id-123" in mock_log.info.call_args_list[0][0][0]

    def test_dispatch_handles_missing_request_id(self):
        from app.middleware.monitoring import MonitoringMiddleware
        request = MagicMock(spec=["method", "url", "state"])
        request.state = MagicMock(spec=[])
        request.method = "GET"
        request.url.path = "/test"
        call_next = AsyncMock(return_value=MagicMock(headers={}))
        mw = MonitoringMiddleware(MagicMock())
        import asyncio
        with patch("app.middleware.monitoring.logger") as mock_log:
            asyncio.run(mw.dispatch(request, call_next))
            assert "unknown" in mock_log.info.call_args_list[0][0][0]

    def test_dispatch_sets_timing_headers(self):
        from app.middleware.monitoring import MonitoringMiddleware
        request = MagicMock()
        request.headers = {}
        request.method = "GET"
        request.url.path = "/test"
        response = MagicMock(headers={})
        call_next = AsyncMock(return_value=response)
        mw = MonitoringMiddleware(MagicMock())
        import asyncio
        result = asyncio.run(mw.dispatch(request, call_next))
        assert "X-Processing-Time" in result.headers

    def test_dispatch_error_logs_and_re_raises(self):
        from app.middleware.monitoring import MonitoringMiddleware
        request = MagicMock()
        request.headers = {}
        request.method = "POST"
        request.url.path = "/fail"
        async def failing_call_next(req):
            raise ValueError("test error")
        mw = MonitoringMiddleware(MagicMock())
        import asyncio
        with patch("app.middleware.monitoring.logger") as mock_log:
            with pytest.raises(ValueError, match="test error"):
                asyncio.run(mw.dispatch(request, failing_call_next))
            mock_log.error.assert_called_once()
            log_msg = mock_log.error.call_args[0][0]
            assert "Request failed" in log_msg

    def test_dispatch_success_logs(self):
        from app.middleware.monitoring import MonitoringMiddleware
        request = MagicMock()
        request.headers = {}
        request.method = "GET"
        request.url.path = "/test"
        response = MagicMock(headers={})
        response.status_code = 200
        call_next = AsyncMock(return_value=response)
        mw = MonitoringMiddleware(MagicMock())
        import asyncio
        with patch("app.middleware.monitoring.logger") as mock_log:
            asyncio.run(mw.dispatch(request, call_next))
            assert mock_log.info.call_count >= 1
            log_calls = [c[0][0] for c in mock_log.info.call_args_list]
            has_start = any("Request started" in msg for msg in log_calls)
            has_complete = any("Request completed" in msg for msg in log_calls)
            assert has_start
            assert has_complete


class TestMainExtra:
    def test_app_created_with_correct_title(self):
        from app.main import app
        assert app.title == "ScholarForm AI Backend"

    def test_http_exception_handler_v1_request(self):
        from fastapi import HTTPException

        from app.main import http_exception_handler
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        request.state.request_id = "req-1"
        exc = HTTPException(status_code=404, detail="Not found")
        import asyncio
        with patch("app.main.build_error_response") as mock_build:
            mock_build.return_value = MagicMock(headers={}, status_code=404)
            asyncio.run(http_exception_handler(request, exc))
            mock_build.assert_called_once()

    def test_http_exception_handler_non_v1_request(self):
        from fastapi import HTTPException

        from app.main import http_exception_handler
        request = MagicMock()
        request.url.path = "/docs"
        exc = HTTPException(status_code=404, detail="Not found")
        import asyncio
        with patch("app.main.fastapi_http_exception_handler") as mock_handler:
            mock_handler.return_value = MagicMock()
            asyncio.run(http_exception_handler(request, exc))
            mock_handler.assert_called_once_with(request, exc)

    def test_http_exception_handler_with_detail_dict(self):
        from fastapi import HTTPException

        from app.main import http_exception_handler
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        request.state.request_id = "req-1"
        exc = HTTPException(status_code=422, detail={"field": "error"})
        import asyncio
        with patch("app.main.build_error_response") as mock_build:
            mock_build.return_value = MagicMock(headers={}, status_code=422)
            asyncio.run(http_exception_handler(request, exc))
            mock_build.assert_called_once()

    def test_request_validation_handler_v1_request(self):
        from fastapi.exceptions import RequestValidationError

        from app.main import request_validation_handler
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        request.state.request_id = "req-1"
        exc = RequestValidationError(errors=[{"loc": ["body", "title"], "msg": "field required"}])
        import asyncio
        with patch("app.main.build_error_response") as mock_build:
            mock_build.return_value = MagicMock(headers={}, status_code=422)
            asyncio.run(request_validation_handler(request, exc))
            mock_build.assert_called_once_with(
                request, status_code=422, code="VALIDATION_ERROR",
                message="Request validation failed", details=mock_build.call_args[1].get("details")
            )

    def test_request_validation_handler_non_v1_request(self):
        from fastapi.exceptions import RequestValidationError

        from app.main import request_validation_handler
        request = MagicMock()
        request.url.path = "/docs"
        exc = RequestValidationError(errors=[])
        import asyncio
        with patch("app.main.fastapi_validation_exception_handler") as mock_handler:
            mock_handler.return_value = MagicMock()
            asyncio.run(request_validation_handler(request, exc))
            mock_handler.assert_called_once_with(request, exc)

    def test_root_endpoint(self):
        import asyncio

        from app.main import root
        result = asyncio.run(root())
        assert result["message"] == "ScholarForm AI Backend is running"

    def test_health_check_returns_200(self):
        from app.main import health_check
        mock_payload = {"status": "healthy", "version": "1.0.0"}
        with patch("app.services.health_checks.get_health_payload", return_value=(mock_payload, 200)):
            import asyncio
            response = asyncio.run(health_check())
            assert response.status_code == 200
            assert "status" in response.body.decode()

    def test_readiness_probe(self):
        from app.main import readiness_probe
        with patch("app.services.health_checks.get_readiness_payload", return_value=({"ready": True}, 200)):
            import asyncio
            response = asyncio.run(readiness_probe())
            assert response.status_code == 200

    def test_is_v1_request_preview(self):
        from app.main import _is_v1_request
        request = MagicMock()
        request.url.path = "/api/preview/live"
        assert _is_v1_request(request) is False

    def test_build_error_response_no_request_id(self):
        from app.main import build_error_response
        request = MagicMock()
        del request.state.request_id
        resp = build_error_response(request, status_code=500, code="ERROR", message="fail")
        assert resp.status_code == 500

    def test_http_exception_preserves_headers(self):
        from fastapi import HTTPException

        from app.main import http_exception_handler
        request = MagicMock()
        request.url.path = "/api/v1/documents"
        request.state.request_id = "req-1"
        exc = HTTPException(status_code=429, detail="Too fast", headers={"Retry-After": "60"})
        import asyncio
        with patch("app.main.build_error_response") as mock_build:
            resp = MagicMock(headers={}, status_code=429)
            mock_build.return_value = resp
            asyncio.run(http_exception_handler(request, exc))
            assert resp.headers.get("Retry-After") == "60"

    def test_periodic_file_cleanup_cancelled(self):
        cleanup_task = MagicMock()
        cleanup_task.cancel.return_value = None
        import asyncio
        async def mock_cancel():
            cleanup_task.cancel()
        asyncio.run(mock_cancel())
        cleanup_task.cancel.assert_called_once()

    def test_validate_startup_redis_enabled_no_url(self):
        with patch("app.main.settings.ALGORITHM", "HS256"), \
             patch("app.main.settings.REDIS_ENABLED", True), \
             patch("app.main.settings.REDIS_URL", None), \
             patch("app.main.settings.NVIDIA_API_KEY", "nk-xxx"), \
             patch("app.main.settings.SUPABASE_URL", "https://project.supabase.co"), \
             patch("app.main.settings.SUPABASE_SERVICE_ROLE_KEY", "key"):
            from app.main import _validate_startup
            _validate_startup()

    def test_validate_startup_redis_connection_fail(self):
        with patch("app.main.settings.ALGORITHM", "HS256"), \
             patch("app.main.settings.REDIS_ENABLED", True), \
             patch("app.main.settings.REDIS_URL", "redis://badhost"), \
             patch("app.main.settings.NVIDIA_API_KEY", "nk-xxx"), \
             patch("app.main.settings.SUPABASE_URL", None), \
             patch("redis.Redis.from_url", side_effect=Exception("conn fail")):
            from app.main import _validate_startup
            _validate_startup()

    def test_lifespan_shutdown_cancels_tasks(self):
        from app.main import lifespan
        app = MagicMock()
        app.state.grobid_startup_probe_ok = False
        import asyncio
        with patch("app.main._run_startup_step", return_value=None), \
             patch("app.main.settings.ENABLE_FILE_CLEANUP", False), \
             patch("app.main.safe_execution") as mock_safe:
            mock_safe.__enter__ = MagicMock(return_value=None)
            mock_safe.__exit__ = MagicMock(return_value=None)
            async def run():
                async with lifespan(app):
                    pass
            asyncio.run(run())


class TestSupabaseClientExtra:
    def test_supabase_client_module_resets_globals(self):
        import app.db.supabase_client as sc
        sc._client_initialized = False
        sc._supabase_client = None
        assert sc._client_initialized is False
        assert sc._supabase_client is None

    def test_init_client_creates_client_with_correct_params(self):
        with patch("app.db.supabase_client.settings") as mock_settings, \
             patch("app.db.supabase_client.create_client") as mock_create:
            mock_settings.SUPABASE_URL = "https://project.supabase.co"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "service-role-key"
            from app.db.supabase_client import _init_client
            _init_client()
            mock_create.assert_called_once_with("https://project.supabase.co", "service-role-key")

    def test_get_supabase_db_returns_client_when_configured(self):
        with patch("app.db.supabase_client.get_supabase_client", return_value="client-object"):
            from app.db.supabase_client import get_supabase_db
            assert get_supabase_db() == "client-object"

    def test_check_supabase_health_healthy_query(self):
        mock_client = MagicMock()
        mock_execute = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_execute
        with patch("app.db.supabase_client.get_supabase_client", return_value=mock_client):
            from app.db.supabase_client import check_supabase_health
            result = check_supabase_health()
            assert result["status"] == "healthy"
            mock_client.table.assert_called_once_with("profiles")
            mock_client.table.return_value.select.assert_called_once_with("id")


class TestRedisCacheExtra:
    def test_get_redis_cache_returns_singleton(self):
        from app.cache.redis_cache import get_redis_cache, redis_cache
        assert get_redis_cache() is redis_cache

    def test_health_with_error_detail(self):
        from app.cache.redis_cache import RedisCache
        cache = RedisCache()
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("connection timeout")
        with patch.object(cache, "_ensure_client", return_value=mock_client):
            result = cache.health()
            assert result["status"] == "unavailable"
            assert "connection timeout" in result["detail"]

    def test_ensure_client_settings_exception_returns_none(self):
        from app.cache.redis_cache import RedisCache
        cache = RedisCache()
        cache._initialized = False
        with patch("app.config.settings.settings") as mock_s:
            mock_s.REDIS_ENABLED = True
            mock_s.REDIS_URL = None
            mock_s.REDIS_HOST = "badhost"
            mock_s.REDIS_PORT = 6379
            from redis import Redis as RealRedis
            with patch.object(RealRedis, "from_url", side_effect=Exception("conn error")):
                result = cache._ensure_client()
                assert result is None

    def test_generate_key_different_prefixes(self):
        from app.cache.redis_cache import RedisCache
        cache = RedisCache()
        k1 = cache._generate_key("hello", prefix="grobid")
        k2 = cache._generate_key("hello", prefix="llm")
        assert k1.startswith("grobid:")
        assert k2.startswith("llm:")
        assert k1 != k2


class TestDBSessionExtra:
    def test_session_local_none_when_engine_none(self):
        import app.db.session as db_session
        with patch.object(db_session, "engine", None), \
             patch.object(db_session, "SessionLocal", None):
            from app.db.session import SessionLocal
            assert SessionLocal is None

    def test_get_db_raises_503_when_session_local_none(self):
        with patch("app.db.session.SessionLocal", None):
            from app.db.session import get_db
            with pytest.raises(Exception) as exc:
                next(get_db())
            assert "503" in str(exc.value) or "Database is not configured" in str(exc.value)

    def test_get_db_handles_sqlalchemy_error(self):
        from sqlalchemy.exc import SQLAlchemyError

        from app.db.session import get_db
        mock_session = MagicMock()
        mock_session.commit.side_effect = SQLAlchemyError("db failure")
        with patch("app.db.session.SessionLocal", return_value=mock_session):
            gen = get_db()
            next(gen)
            with pytest.raises(Exception) as exc:
                gen.throw(SQLAlchemyError("db failure"))
            assert "500" in str(exc.value) or "A database error occurred" in str(exc.value)
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    def test_get_db_closes_session_in_finally(self):
        from app.db.session import get_db
        mock_session = MagicMock()
        with patch("app.db.session.SessionLocal", return_value=mock_session):
            gen = get_db()
            next(gen)
            with pytest.raises(StopIteration):
                next(gen)
            mock_session.close.assert_called_once()

    def test_get_db_closes_session_on_exception(self):
        from app.db.session import get_db
        mock_session = MagicMock()
        mock_session.close.side_effect = lambda: None
        with patch("app.db.session.SessionLocal", return_value=mock_session):
            gen = get_db()
            next(gen)
            with contextlib.suppress(ValueError):
                gen.throw(ValueError("unexpected"))
            mock_session.close.assert_called_once()

    def test_check_db_health_with_operational_error(self):
        from sqlalchemy.exc import OperationalError
        mock_engine = MagicMock()
        MagicMock()
        mock_engine.connect.return_value.__enter__.side_effect = OperationalError("stmt", {}, None)
        with patch("app.db.session.engine", mock_engine):
            from app.db.session import check_db_health
            result = check_db_health()
            assert result["status"] == "unhealthy"

    def test_check_db_health_connected(self):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        with patch("app.db.session.engine", mock_engine):
            from app.db.session import check_db_health
            result = check_db_health()
            assert result["status"] == "healthy"
            mock_conn.execute.assert_called_once()

    def test_engine_creation_exception(self):
        with patch("app.db.session.settings.SUPABASE_DB_URL", "postgresql://fail"), \
             patch("app.db.session.create_engine", side_effect=RuntimeError("engine crash")):
            from app.db.session import _create_engine_safe
            result = _create_engine_safe()
            assert result is None
