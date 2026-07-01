from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestAbuseDetector:
    def test_init(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = None
            d = AbuseDetector()
            assert d._redis is None
            assert d._memory == {}

    def test_increment_bucket_redis(self):
        from app.middleware.abuse_detector import AbuseDetector
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 5
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = mock_redis
            d = AbuseDetector()
            count = d._increment_bucket("test:key", 300)
            assert count == 5

    def test_increment_bucket_redis_first_call(self):
        from app.middleware.abuse_detector import AbuseDetector
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = mock_redis
            d = AbuseDetector()
            count = d._increment_bucket("test:key", 300)
            assert count == 1
            mock_redis.expire.assert_called_once()

    def test_increment_bucket_redis_fallback_to_memory(self):
        from app.middleware.abuse_detector import AbuseDetector
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = Exception("Redis down")
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = mock_redis
            d = AbuseDetector()
            count = d._increment_bucket("test:key", 300)
            assert count == 1
            count2 = d._increment_bucket("test:key", 300)
            assert count2 == 2

    @pytest.mark.asyncio
    async def test_record_generation_request_below_threshold(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = MagicMock()
            d = AbuseDetector()
            with patch.object(d, "_increment_bucket", return_value=1):
                await d.record_generation_request("1.2.3.4")

    @pytest.mark.asyncio
    async def test_record_generation_request_above_threshold(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = MagicMock()
            d = AbuseDetector()
            with patch.object(d, "_increment_bucket", return_value=11):
                with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                    mock_audit.log = AsyncMock()
                    await d.record_generation_request("1.2.3.4")
                    mock_audit.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_generation_request_empty_ip(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = MagicMock()
            d = AbuseDetector()
            with patch.object(d, "_increment_bucket", return_value=1):
                await d.record_generation_request("")

    @pytest.mark.asyncio
    async def test_record_llm_call_below_threshold(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = MagicMock()
            d = AbuseDetector()
            with patch.object(d, "_increment_bucket", return_value=10):
                await d.record_llm_call("user1")

    @pytest.mark.asyncio
    async def test_record_llm_call_above_threshold(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = MagicMock()
            d = AbuseDetector()
            with patch.object(d, "_increment_bucket", return_value=51):
                with patch("app.middleware.abuse_detector.audit_log_service") as mock_audit:
                    mock_audit.log = AsyncMock()
                    await d.record_llm_call("user1")
                    mock_audit.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_llm_call_anonymous(self):
        from app.middleware.abuse_detector import AbuseDetector
        with patch("app.middleware.abuse_detector.RedisCache") as mock_rc:
            mock_rc.return_value.client = MagicMock()
            d = AbuseDetector()
            with patch.object(d, "_increment_bucket", return_value=1):
                await d.record_llm_call(None)

    def test_abuse_detector_singleton(self):
        from app.middleware.abuse_detector import abuse_detector
        assert abuse_detector is not None
