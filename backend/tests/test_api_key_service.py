# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Tests for API Key service, encryption, rate limiter, and feature flags.
Covers the new Phase 2 implementation.
"""
from __future__ import annotations

import time
import pytest
from unittest.mock import MagicMock, patch

from app.services.encryption_service import EncryptionService, get_encryption_service
from app.services.api_key_rate_limiter import ApiKeyRateLimiter, get_api_key_rate_limiter, RateLimitResult


class TestEncryptionService:
    """Tests for Fernet encryption service."""

    def test_encrypt_decrypt_roundtrip(self):
        service = EncryptionService()
        plaintext = "sk-test-secret-key-12345"
        encrypted = service.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_raises(self):
        service = EncryptionService()
        with pytest.raises(ValueError, match="empty"):
            service.encrypt("")

    def test_decrypt_empty_raises(self):
        service = EncryptionService()
        with pytest.raises(ValueError, match="empty"):
            service.decrypt("")

    def test_decrypt_wrong_key_raises(self):
        service1 = EncryptionService()
        service2 = EncryptionService()
        encrypted = service1.encrypt("secret")
        with pytest.raises(ValueError, match="Decryption failed"):
            service2.decrypt(encrypted)

    def test_generate_key(self):
        key1 = EncryptionService.generate_key()
        key2 = EncryptionService.generate_key()
        assert key1 != key2
        assert len(key1) > 20

    def test_get_encryption_service_singleton(self):
        s1 = get_encryption_service()
        s2 = get_encryption_service()
        assert s1 is s2

    def test_encrypt_produces_different_ciphertext(self):
        service = EncryptionService()
        enc1 = service.encrypt("same-plaintext")
        enc2 = service.encrypt("same-plaintext")
        assert enc1 != enc2


class TestApiKeyRateLimiter:
    """Tests for per-key rate limiter using in-memory backend."""

    @pytest.fixture(autouse=True)
    def _no_redis(self):
        with patch.object(ApiKeyRateLimiter, "_get_redis", return_value=None):
            yield

    def test_within_limit_allowed(self):
        limiter = ApiKeyRateLimiter()
        result = limiter.check_rate_limit("key-1", per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is True
        assert result.remaining >= 0

    def test_exceed_minute_limit(self):
        limiter = ApiKeyRateLimiter()
        key = "key-minute-test"
        for _ in range(60):
            limiter.check_rate_limit(key, per_minute=60, per_hour=1000, per_day=10000)
        result = limiter.check_rate_limit(key, per_minute=60, per_hour=1000, per_day=10000)
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.retry_after > 0

    def test_exceed_hour_limit(self):
        limiter = ApiKeyRateLimiter()
        key = "key-hour-test"
        for _ in range(1000):
            limiter.check_rate_limit(key, per_minute=10000, per_hour=1000, per_day=10000)
        result = limiter.check_rate_limit(key, per_minute=10000, per_hour=1000, per_day=10000)
        assert result.allowed is False

    def test_exceed_day_limit(self):
        limiter = ApiKeyRateLimiter()
        key = "key-day-test"
        for _ in range(10000):
            limiter.check_rate_limit(key, per_minute=100000, per_hour=100000, per_day=10000)
        result = limiter.check_rate_limit(key, per_minute=100000, per_hour=100000, per_day=10000)
        assert result.allowed is False

    def test_different_keys_independent(self):
        limiter = ApiKeyRateLimiter()
        limiter.check_rate_limit("key-a", per_minute=1, per_hour=1000, per_day=10000)
        limiter.check_rate_limit("key-a", per_minute=1, per_hour=1000, per_day=10000)
        result_a = limiter.check_rate_limit("key-a", per_minute=1, per_hour=1000, per_day=10000)
        result_b = limiter.check_rate_limit("key-b", per_minute=1, per_hour=1000, per_day=10000)
        assert result_a.allowed is False
        assert result_b.allowed is True

    def test_get_usage_returns_counts(self):
        limiter = ApiKeyRateLimiter()
        key = "key-usage-test"
        limiter.check_rate_limit(key, per_minute=100, per_hour=1000, per_day=10000)
        limiter.check_rate_limit(key, per_minute=100, per_hour=1000, per_day=10000)
        usage = limiter.get_usage(key)
        assert usage["requests_this_minute"] == 2

    def test_get_api_key_rate_limiter_singleton(self):
        l1 = get_api_key_rate_limiter()
        l2 = get_api_key_rate_limiter()
        assert l1 is l2

    def test_rate_limit_result_dataclass(self):
        result = RateLimitResult(
            allowed=True, limit=60, remaining=55, reset_at=time.time() + 60
        )
        assert result.allowed is True
        assert result.limit == 60
        assert result.remaining == 55
        assert result.retry_after is None

    def test_rate_limit_result_with_retry(self):
        result = RateLimitResult(
            allowed=False, limit=60, remaining=0, reset_at=time.time() + 30, retry_after=30.0
        )
        assert result.allowed is False
        assert result.retry_after == 30.0
