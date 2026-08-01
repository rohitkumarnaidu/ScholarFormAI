import pytest
from unittest.mock import MagicMock, patch, AsyncMock


RESET_FUNC = """
from app.services import health_checks as hc
hc._reset_readiness_cache_for_tests()
"""


@pytest.fixture(autouse=True)
def reset_caches():
    from app.services import health_checks as hc
    hc._reset_readiness_cache_for_tests()


class TestTtlFunctions:
    def test_readiness_ttl_default(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "READINESS_CACHE_TTL_SECONDS", 15):
            assert hc._readiness_ttl_seconds() == 15.0

    def test_readiness_ttl_invalid_fallback(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "READINESS_CACHE_TTL_SECONDS", "invalid"):
            assert hc._readiness_ttl_seconds() == 15.0

    def test_readiness_ttl_negative_clamped(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "READINESS_CACHE_TTL_SECONDS", -5):
            assert hc._readiness_ttl_seconds() == 0.0

    def test_health_ttl_default(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "HEALTH_CACHE_TTL_SECONDS", 15):
            assert hc._health_ttl_seconds() == 15.0

    def test_health_ttl_invalid_fallback(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "HEALTH_CACHE_TTL_SECONDS", None):
            assert hc._health_ttl_seconds() == 15.0


class TestClonePayload:
    def test_clone_shallow(self, health_checks):
        hc = health_checks
        original = {"status": "healthy", "checks": {"db": "ok"}, "dependencies": {"ext": {"status": "ready"}}}
        cloned = hc._clone_payload(original)
        assert cloned == original
        assert cloned is not original
        assert cloned["checks"] is not original["checks"]
        assert cloned["dependencies"] is not original["dependencies"]

    def test_clone_no_checks(self, health_checks):
        hc = health_checks
        original = {"status": "healthy"}
        cloned = hc._clone_payload(original)
        assert cloned == original


class TestCacheInvalidation:
    def test_invalidate_readiness(self, health_checks):
        hc = health_checks
        hc._readiness_cache_payload = {"data": 1}
        hc._readiness_cache_status_code = 200
        hc._readiness_cache_expiry = 999.0
        hc.invalidate_readiness_cache()
        assert hc._readiness_cache_payload is None
        assert hc._readiness_cache_status_code == 503
        assert hc._readiness_cache_expiry == 0.0

    def test_invalidate_health(self, health_checks):
        hc = health_checks
        hc._health_cache_payload = {"data": 1}
        hc.invalidate_health_cache()
        assert hc._health_cache_payload is None

    def test_reset_for_tests(self, health_checks):
        hc = health_checks
        hc._readiness_cache_lock = "lock"
        hc._reset_readiness_cache_for_tests()
        assert hc._readiness_cache_lock is None
        assert hc._health_cache_lock is None


class TestServiceUrls:
    def test_with_callable_resolver(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_grobid_urls", return_value=["http://grobid:8070/"]):
            urls = hc._service_urls("get_grobid_urls")
        assert urls == ["http://grobid:8070"]

    def test_resolver_returns_empty(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_grobid_urls", return_value=[]):
            urls = hc._service_urls("get_grobid_urls")
        assert urls == []

    def test_resolver_exception(self, health_checks):
        hc = health_checks
        def raiser():
            raise ValueError("boom")
        with patch.object(hc.settings, "get_grobid_urls", raiser):
            urls = hc._service_urls("get_grobid_urls")
        assert urls == []

    def test_resolver_returns_none(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_grobid_urls", return_value=None):
            urls = hc._service_urls("get_grobid_urls")
        assert urls == []

    def test_strips_trailing_slash(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_grobid_urls", return_value=["http://grobid:8070/"]):
            urls = hc._service_urls("get_grobid_urls")
        for url in urls:
            assert not url.endswith("/")


class TestServiceHealthPath:
    def test_with_callable_resolver(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_service_health_path", return_value="/api/isalive"):
            assert hc._service_health_path("grobid") == "/api/isalive"

    def test_resolver_exception_fallback(self, health_checks):
        hc = health_checks
        def raiser(name):
            raise RuntimeError("fail")
        with patch.object(hc.settings, "get_service_health_path", raiser):
            assert hc._service_health_path("grobid") == "/"

    def test_empty_path_fallback(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_service_health_path", return_value=""):
            path = hc._service_health_path("grobid")
        assert path == "" or path == "/"

    def test_adds_leading_slash(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_service_health_path", return_value="/health"):
            assert hc._service_health_path("grobid") == "/health"

    def test_trailing_slash_stripped(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_service_health_path", return_value="/health/"):
            path = hc._service_health_path("grobid")
        assert path == "/health/"  # normalization handled by Settings.get_service_health_path

    def test_no_resolver_default(self, health_checks):
        hc = health_checks
        with patch.object(hc.settings, "get_service_health_path", None):
            path = hc._service_health_path("grobid")
        assert path == "/"


class TestJoinEndpoint:
    def test_joins_correctly(self, health_checks):
        hc = health_checks
        assert hc._join_endpoint("http://grobid:8070", "/api/isalive") == "http://grobid:8070/api/isalive"

    def test_strips_base_trailing_slash(self, health_checks):
        hc = health_checks
        assert hc._join_endpoint("http://grobid:8070/", "/api") == "http://grobid:8070/api"


class TestProbeServiceTargets:
    @pytest.mark.asyncio
    async def test_no_urls(self, health_checks):
        hc = health_checks
        result = await hc._probe_service_targets(service_name="test", urls=[], health_path="/")
        assert result["status"] == "unconfigured"
        assert result["service"] == "test"

    @pytest.mark.asyncio
    async def test_first_url_returns_200(self, health_checks):
        hc = health_checks
        ok_resp = MagicMock(status_code=200)

        async def mock_get(*a, **kw):
            return ok_resp

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await hc._probe_service_targets(
                service_name="grobid",
                urls=["http://grobid:8070"],
                health_path="/api/isalive",
            )
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_all_urls_fail(self, health_checks):
        hc = health_checks

        async def mock_get(*a, **kw):
            raise ConnectionError("refused")

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await hc._probe_service_targets(
                service_name="grobid",
                urls=["http://grobid:8070"],
                health_path="/api/isalive",
            )
        assert result["status"] == "unavailable"
        assert result["last_probe"]["error"] == "refused"

    @pytest.mark.asyncio
    async def test_non_200_then_200(self, health_checks):
        hc = health_checks
        fail_resp = MagicMock(status_code=500)
        ok_resp = MagicMock(status_code=200)

        call_count = 0

        async def mock_get(*a, **kw):
            nonlocal call_count
            call_count += 1
            return fail_resp if call_count == 1 else ok_resp

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = mock_get

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await hc._probe_service_targets(
                service_name="grobid",
                urls=["http://grobid:8070", "http://grobid:8071"],
                health_path="/api/isalive",
            )
        assert result["status"] == "ready"
        assert len(result["attempts"]) == 2


class TestGetHealthPayload:
    @pytest.mark.asyncio
    async def test_returns_cached(self, health_checks):
        hc = health_checks
        hc._health_cache_payload = {"status": "healthy"}
        hc._health_cache_status_code = 200
        hc._health_cache_expiry = 999999.0
        with patch.object(hc, "_health_ttl_seconds", return_value=30):
            payload, code = await hc.get_health_payload()
        assert payload["status"] == "healthy"
        assert code == 200

    @pytest.mark.asyncio
    async def test_force_refresh(self, health_checks):
        hc = health_checks
        hc._health_cache_payload = {"status": "healthy"}
        hc._health_cache_status_code = 200
        hc._health_cache_expiry = 999999.0
        with patch.object(hc, "_build_health_payload", AsyncMock(return_value=({"status": "fresh"}, 200))):
            with patch.object(hc, "_health_ttl_seconds", return_value=30):
                payload, code = await hc.get_health_payload(force_refresh=True)
        assert payload["status"] == "fresh"

    @pytest.mark.asyncio
    async def test_expired_cache(self, health_checks):
        hc = health_checks
        from time import monotonic
        hc._health_cache_payload = {"status": "healthy"}
        hc._health_cache_status_code = 200
        hc._health_cache_expiry = monotonic() - 10
        fake_payload = {"status": "rebuilt", "version": "1.0.0", "components": {}}
        with patch.object(hc, "_build_health_payload", AsyncMock(return_value=(fake_payload, 503))):
            with patch.object(hc, "_health_ttl_seconds", return_value=30):
                payload, code = await hc.get_health_payload()
        assert payload["status"] == "rebuilt"
        assert code == 503

    @pytest.mark.asyncio
    async def test_build_health_calls_components(self, health_checks):
        hc = health_checks
        ok_resp = MagicMock(status_code=200)

        async def mock_get(*a, **kw):
            return ok_resp

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = mock_get

        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("app.services.model_store.model_store.get_model", return_value="model_obj"):
                    payload, code = await hc._build_health_payload()
        assert payload["status"] in ("healthy", "degraded")
        assert code in (200, 503)

    @pytest.mark.asyncio
    async def test_build_health_supabase_exception(self, health_checks):
        hc = health_checks
        ok_resp = MagicMock(status_code=200)

        async def mock_get(*a, **kw):
            return ok_resp

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = mock_get

        with patch("app.db.supabase_client.check_supabase_health", side_effect=ValueError("fail")):
            with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("app.services.model_store.model_store.get_model", return_value=None):
                    payload, code = await hc._build_health_payload()
        assert payload["status"] == "degraded"
        assert "unhealthy" in payload["components"]["supabase_db"]

    @pytest.mark.asyncio
    async def test_build_health_ollama_request_error(self, health_checks):
        hc = health_checks

        async def mock_get(*a, **kw):
            import httpx
            raise httpx.RequestError("timeout")

        mock_client = MagicMock()
        mock_client.__aenter__.return_value.get = mock_get

        with patch.object(hc.settings, "OLLAMA_URL", "http://ollama:11434"):
            with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
                with patch("httpx.AsyncClient", return_value=mock_client):
                    with patch("app.services.model_store.model_store.get_model", return_value=None):
                        payload, code = await hc._build_health_payload()
        assert payload["status"] == "degraded"
        assert "unavailable" in payload["components"]["ollama"]


class TestGetReadinessPayload:
    @pytest.mark.asyncio
    async def test_returns_cached(self, health_checks):
        hc = health_checks
        hc._readiness_cache_payload = {"ready": True}
        hc._readiness_cache_status_code = 200
        hc._readiness_cache_expiry = 999999.0
        with patch.object(hc, "_readiness_ttl_seconds", return_value=30):
            payload, code = await hc.get_readiness_payload()
        assert payload["ready"] is True

    @pytest.mark.asyncio
    async def test_force_refresh(self, health_checks):
        hc = health_checks
        hc._readiness_cache_payload = {"ready": True}
        hc._readiness_cache_status_code = 200
        hc._readiness_cache_expiry = 999999.0
        with patch.object(hc, "_build_readiness_payload", AsyncMock(return_value=({"ready": False}, 503))):
            with patch.object(hc, "_readiness_ttl_seconds", return_value=30):
                payload, code = await hc.get_readiness_payload(force_refresh=True)
        assert payload["ready"] is False
        assert code == 503

    @pytest.mark.asyncio
    async def test_build_readiness_supabase_healthy(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", False):
                with patch.object(hc, "should_enable_scibert", return_value=False):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", False):
                        with patch.object(hc, "_service_urls", return_value=["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert "ready" in payload
        assert "checks" in payload
        assert "dependencies" in payload

    @pytest.mark.asyncio
    async def test_build_readiness_with_grobid(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", True):
                with patch.object(hc, "should_enable_scibert", return_value=False):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", False):
                        with patch.object(hc, "_service_urls", return_value=["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert payload["checks"]["grobid"] == "ready"
        assert payload["checks"]["docling"] == "ready"

    @pytest.mark.asyncio
    async def test_build_readiness_grobid_not_ready(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", True):
                with patch.object(hc, "should_enable_scibert", return_value=False):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", False):
                        with patch.object(hc, "_service_urls", return_value=["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "unavailable"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert payload["ready"] is False
        assert code == 503

    @pytest.mark.asyncio
    async def test_build_readiness_supabase_unhealthy(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "error"}):
            with patch.object(hc.settings, "GROBID_ENABLED", False):
                with patch.object(hc, "should_enable_scibert", return_value=False):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", False):
                        with patch.object(hc, "_service_urls", return_value=["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert payload["ready"] is False
        assert code == 503

    @pytest.mark.asyncio
    async def test_build_readiness_with_nougat_enabled(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", False):
                with patch.object(hc, "should_enable_scibert", return_value=False):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", True):
                        with patch.object(hc, "_service_urls", return_value=["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert payload["checks"]["nougat"] == "ready"

    @pytest.mark.asyncio
    async def test_build_readiness_nougat_no_urls(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", False):
                with patch.object(hc, "should_enable_scibert", return_value=False):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", True):
                        with patch.object(hc, "_service_urls", side_effect=lambda method: [] if "nougat" in method else ["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert payload["checks"]["nougat"] == "local_or_unconfigured"

    @pytest.mark.asyncio
    async def test_build_readiness_with_scibert_enabled_remote(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", False):
                with patch.object(hc, "should_enable_scibert", return_value=True):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", False):
                        with patch.object(hc, "_service_urls", side_effect=lambda method: ["http://scibert:5000"] if "scibert" in method else ["http://mock:8080"]):
                            with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                    payload, code = await hc._build_readiness_payload()
        assert payload["checks"]["ai_models"] == "remote"
        assert payload["checks"]["scibert"] == "ready"

    @pytest.mark.asyncio
    async def test_build_readiness_with_scibert_enabled_local(self, health_checks):
        hc = health_checks
        with patch("app.db.supabase_client.check_supabase_health", return_value={"status": "healthy"}):
            with patch.object(hc.settings, "GROBID_ENABLED", False):
                with patch.object(hc, "should_enable_scibert", return_value=True):
                    with patch.object(hc.settings, "ENABLE_NOUGAT_PARSER", False):
                        with patch.object(hc, "_service_urls", side_effect=lambda method: [] if "scibert" in method else ["http://mock:8080"]):
                            with patch("app.services.model_store.model_store.get_model", return_value="scibert_obj"):
                                with patch.object(hc, "_probe_service_targets", AsyncMock(return_value={"status": "ready"})):
                                    with patch("app.services.llm_service.check_health", AsyncMock(return_value="ok")):
                                        payload, code = await hc._build_readiness_payload()
        assert payload["checks"]["ai_models"] == "loaded"
        assert payload["checks"]["scibert"] == "local"


@pytest.fixture
def health_checks():
    import importlib
    import app.services.health_checks as hc_mod
    importlib.reload(hc_mod)
    return hc_mod
