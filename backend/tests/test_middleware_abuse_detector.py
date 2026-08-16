import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAbuseDetector:
    def test_increment_bucket_with_redis(self):
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = mock_redis
            from app.middleware.abuse_detector import AbuseDetector

            detector = AbuseDetector()
            count = detector._increment_bucket("test:ip", window_seconds=300)
            assert count == 1
            mock_redis.incr.assert_called_once()
            mock_redis.expire.assert_called_once()

    def test_increment_bucket_redis_exception(self):
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = ConnectionError("redis down")
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = mock_redis
            from app.middleware.abuse_detector import AbuseDetector

            detector = AbuseDetector()
            detector._redis_warning_logged = False
            count = detector._increment_bucket("test:ip", window_seconds=300)
            assert count == 1  # falls back to in-memory

    def test_increment_bucket_no_redis(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            from app.middleware.abuse_detector import AbuseDetector

            detector = AbuseDetector()
            count = detector._increment_bucket("test:ip", window_seconds=300)
            assert count == 1

    def test_increment_bucket_in_memory_multiple(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            from app.middleware.abuse_detector import AbuseDetector

            detector = AbuseDetector()
            detector._increment_bucket("test:ip", window_seconds=300)
            count = detector._increment_bucket("test:ip", window_seconds=300)
            assert count == 2

    def test_increment_bucket_in_memory_eviction(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            from app.middleware.abuse_detector import AbuseDetector

            detector = AbuseDetector()
            old = time.time() - 600
            detector._memory[("test:ip", "300")] = [old]
            count = detector._increment_bucket("test:ip", window_seconds=300)
            assert count == 1  # old evicted

    @pytest.mark.asyncio
    async def test_record_generation_request_under_threshold(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                mock_audit.log = AsyncMock()
                from app.middleware.abuse_detector import AbuseDetector

                detector = AbuseDetector()
                await detector.record_generation_request("1.2.3.4")
                mock_audit.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_generation_request_over_threshold(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                mock_audit.log = AsyncMock()
                from app.middleware.abuse_detector import AbuseDetector

                detector = AbuseDetector()
                for _ in range(11):
                    await detector.record_generation_request("1.2.3.4")
                mock_audit.log.assert_called_once()
                assert mock_audit.log.call_args[1]["details"]["type"] == "generation_spike"

    @pytest.mark.asyncio
    async def test_record_generation_request_no_ip(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                mock_audit.log = AsyncMock()
                from app.middleware.abuse_detector import AbuseDetector

                detector = AbuseDetector()
                for _ in range(12):
                    await detector.record_generation_request("")
                assert mock_audit.log.call_count == 2  # called for count=11 and count=12

    @pytest.mark.asyncio
    async def test_record_llm_call_under_threshold(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                mock_audit.log = AsyncMock()
                from app.middleware.abuse_detector import AbuseDetector

                detector = AbuseDetector()
                await detector.record_llm_call("user-123")
                mock_audit.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_llm_call_over_threshold(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                mock_audit.log = AsyncMock()
                from app.middleware.abuse_detector import AbuseDetector

                detector = AbuseDetector()
                for _ in range(51):
                    await detector.record_llm_call("user-123")
                mock_audit.log.assert_called_once()
                assert mock_audit.log.call_args[1]["details"]["type"] == "llm_overuse"

    @pytest.mark.asyncio
    async def test_record_llm_call_anonymous(self):
        with patch("app.middleware.abuse_detector.RedisCache") as mock_cache:
            mock_cache.return_value.client = None
            with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                mock_audit.log = AsyncMock()
                from app.middleware.abuse_detector import AbuseDetector

                detector = AbuseDetector()
                for _ in range(51):
                    await detector.record_llm_call(None)
                mock_audit.log.assert_called_once()
