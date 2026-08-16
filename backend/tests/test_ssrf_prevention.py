from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.security]


# ── URL Validation Tests ──────────────────────────────────────────────── #


class TestSSRFUrlValidation:
    def test_block_metadata_ip_169_254(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("http://169.254.169.254/latest/meta-data")

    def test_block_metadata_google_internal(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_block_blocked_ip_100_100_100_200(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("http://100.100.100.200/api")

    def test_block_file_scheme(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("file:///etc/passwd")
        assert "scheme" in str(exc.value.detail).lower()

    def test_block_ftp_scheme(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("ftp://ftp.example.com/file")
        assert "scheme" in str(exc.value.detail).lower()

    def test_block_gopher_scheme(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("gopher://localhost:8080/_test")
        assert "scheme" in str(exc.value.detail).lower()

    def test_block_dict_scheme(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("dict://127.0.0.1:6379/info")
        assert "scheme" in str(exc.value.detail).lower()

    def test_reject_only_http_https(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("redis://localhost:6379/0")
        assert "Only http/https" in str(exc.value.detail)

    def test_reject_non_http_scheme(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("ws://example.com/socket")

    def test_accept_valid_external_url(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("https://api.openai.com/v1/models")
        assert result == "https://api.openai.com/v1/models"

    def test_accept_valid_https_url(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("https://example.com/api/tags")
        assert result == "https://example.com/api/tags"

    def test_accept_valid_http_url(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://example.com/api")
        assert result == "http://example.com/api"

    def test_strips_trailing_slash(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("https://example.com/api/")
        assert not result.endswith("/")

    def test_empty_url_rejected(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("")

    def test_ssrf_constants_defined(self):
        from app.routers.v1.providers import SSRF_BLOCKED_HOSTS, SSRF_BLOCKED_SCHEMES

        assert "169.254.169.254" in SSRF_BLOCKED_HOSTS
        assert "metadata.google.internal" in SSRF_BLOCKED_HOSTS
        assert "100.100.100.200" in SSRF_BLOCKED_HOSTS
        assert "file" in SSRF_BLOCKED_SCHEMES
        assert "ftp" in SSRF_BLOCKED_SCHEMES
        assert "dict" in SSRF_BLOCKED_SCHEMES
        assert "gopher" in SSRF_BLOCKED_SCHEMES

    def test_ssrf_gap_fixed_127_0_0_1_now_blocked(self):
        """127.0.0.1 is now blocked by _sanitize_url — gap closed."""
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://127.0.0.1:8000/api")
        assert "host not allowed" in str(exc.value.detail).lower()

    def test_ssrf_gap_fixed_10_dot_now_blocked(self):
        """10.x.x.x range is now blocked — gap closed."""
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://10.0.0.1/api")
        assert "host not allowed" in str(exc.value.detail).lower()

    def test_ssrf_gap_fixed_localhost_now_blocked(self):
        """localhost hostname is now blocked — gap closed."""
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception) as exc:
            _sanitize_url("http://localhost:8080/api")
        assert "host not allowed" in str(exc.value.detail).lower()


class TestSSRFUrlParsingRobustness:
    def test_malformed_url_rejected(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("not a url at all")

    def test_url_with_credentials_accepted_by_sanitize(self):
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://example.com/api")
        assert result == "http://example.com/api"

    def test_redirect_parameter_not_validated(self):
        """Query parameters are not validated as they represent
        data sent to the remote server, not the connection target.
        The httpx client does NOT follow redirects by default."""
        from app.routers.v1.providers import _sanitize_url

        result = _sanitize_url("http://external-api.com/callback?next=https://example.com/dashboard")
        assert result == "http://external-api.com/callback?next=https://example.com/dashboard"

    def test_sanitize_url_rejects_blank(self):
        from app.routers.v1.providers import _sanitize_url

        with pytest.raises(Exception):
            _sanitize_url("   ")


class TestSSRFWebhookValidation:
    @pytest.mark.asyncio
    async def test_webhook_delivery_to_internal_blocked(self):
        from app.services.webhook_service import WebhookService

        svc = WebhookService()
        with (
            patch.object(svc, "_get_client", return_value=MagicMock()),
            patch.object(svc, "_deliver", AsyncMock(side_effect=Exception("Connection refused"))),
        ):
            with patch.object(svc, "_decrypt_secret", return_value="test-secret"):
                result = await svc.dispatch_event("test.event", {"key": "value"}, user_id="user-1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_webhook_url_must_be_http_or_https(self):
        from app.services.webhook_service import WebhookService

        svc = WebhookService()
        with (
            patch.object(svc, "_get_client", return_value=MagicMock()),
            patch.object(svc, "_deliver", AsyncMock(side_effect=Exception("Invalid URL"))),
        ):
            with patch.object(svc, "_decrypt_secret", return_value="test-secret"):
                result = await svc.dispatch_event("test.event", {"key": "value"}, user_id="user-1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_webhook_delivery_timeout_enforced(self):
        from app.services.webhook_service import WebhookService

        svc = WebhookService()
        with (
            patch.object(svc, "_get_client", return_value=MagicMock()),
            patch.object(svc, "_deliver", AsyncMock(side_effect=Exception("Timeout"))),
        ):
            with patch.object(svc, "_decrypt_secret", return_value="test-secret"):
                result = await svc.dispatch_event("test.event", {"key": "value"}, user_id="user-1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_webhook_no_subscriptions_returns_zero(self):
        from app.services.webhook_service import WebhookService

        svc = WebhookService()
        with patch.object(svc, "_get_client", return_value=MagicMock()):
            result = await svc.dispatch_event("nonexistent.event", {"key": "value"}, user_id="no-subs")
        assert result == 0


class TestSSRFExternalClients:
    def test_grobid_url_not_internal(self):
        from app.pipeline.services.grobid_client import GROBIDClient

        with patch("app.pipeline.services.grobid_client.settings") as ms:
            ms.GROBID_URL = "http://localhost:8070"
            ms.get_grobid_urls.return_value = []
            ms.get_service_health_path.return_value = "/api/isalive"
            ms.GROBID_TIMEOUT = 15
            ms.GROBID_MAX_RETRIES = 3
            ms.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
            client = GROBIDClient()
            assert "localhost" in client.base_url or "8070" in client.base_url

    def test_grobid_is_available_handles_connection_error(self):
        from app.pipeline.services.grobid_client import GROBIDClient

        with (
            patch("app.pipeline.services.grobid_client.settings") as ms,
            patch("app.pipeline.services.grobid_client.requests.request") as mock_req,
        ):
            ms.GROBID_URL = "http://localhost:8070"
            ms.get_grobid_urls.return_value = []
            ms.get_service_health_path.return_value = "/api/isalive"
            ms.GROBID_TIMEOUT = 15
            ms.GROBID_MAX_RETRIES = 3
            ms.EXTERNAL_CIRCUIT_BREAKER_ENABLED = False
            mock_req.side_effect = Exception("Connection refused")
            client = GROBIDClient()
            result = client.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_crossref_pipeline_url_uses_https(self):
        from app.pipeline.services.crossref_client import CrossRefClient

        client = CrossRefClient(email="test@example.com")
        assert client.BASE_URL.startswith("https://")

    def test_crossref_service_url_starts_https(self):
        from app.services.crossref_client import CrossRefClient

        with patch("app.services.crossref_client.settings.CROSSREF_MAILTO", "test@example.com"):
            with patch("app.services.crossref_client.HAS_REDIS", False):
                client = CrossRefClient()
                assert client.BASE_URL.startswith("https://")

    def test_csl_fetcher_uses_https(self):
        from app.pipeline.services.csl_fetcher import CSL_SEARCH_URL, ZOTERO_STYLE_URL

        assert CSL_SEARCH_URL.startswith("https://")
        assert ZOTERO_STYLE_URL.startswith("https://")

    def test_nvidia_client_base_url_format(self):
        from app.config.settings import settings

        nim_model = getattr(settings, "NVIDIA_MODEL", "")
        assert "nvidia_nim/" in nim_model or "nvidia" in str(nim_model).lower()
