import pytest
from unittest.mock import MagicMock, patch


class TestSupabaseClient:
    MODULE = "app.db.supabase_client"

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        import app.db.supabase_client as sc
        sc._client_initialized = False
        sc._supabase_client = None

    def test_init_client_no_credentials(self):
        with patch(f"{self.MODULE}.settings") as mock_settings:
            mock_settings.SUPABASE_URL = ""
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = ""
            from app.db.supabase_client import _init_client
            assert _init_client() is None

    def test_init_client_create_client_none(self):
        with patch(f"{self.MODULE}.settings") as mock_settings, \
             patch(f"{self.MODULE}.create_client", None):
            mock_settings.SUPABASE_URL = "https://project.supabase.co"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "service-key"
            from app.db.supabase_client import _init_client
            assert _init_client() is None

    def test_init_client_success(self):
        from app.db.supabase_client import _init_client
        with patch(f"{self.MODULE}.settings") as mock_settings, \
             patch(f"{self.MODULE}.create_client") as mock_create:
            mock_settings.SUPABASE_URL = "https://project.supabase.co"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "service-key"
            mock_create.return_value = "client-instance"
            result = _init_client()
            assert result == "client-instance"
            mock_create.assert_called_once()

    def test_init_client_exception(self):
        with patch(f"{self.MODULE}.settings") as mock_settings, \
             patch(f"{self.MODULE}.create_client") as mock_create:
            mock_settings.SUPABASE_URL = "https://project.supabase.co"
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = "service-key"
            mock_create.side_effect = Exception("init failed")
            from app.db.supabase_client import _init_client
            assert _init_client() is None

    def test_get_supabase_client_initializes(self):
        with patch(f"{self.MODULE}._init_client") as mock_init:
            mock_init.return_value = "client"
            from app.db.supabase_client import get_supabase_client
            result = get_supabase_client()
            assert result == "client"
            assert mock_init.call_count == 1

    def test_get_supabase_client_caches(self):
        with patch(f"{self.MODULE}._init_client") as mock_init:
            mock_init.return_value = "client"
            from app.db.supabase_client import get_supabase_client
            get_supabase_client()
            get_supabase_client()
            assert mock_init.call_count == 1

    def test_get_supabase_client_refresh(self):
        with patch(f"{self.MODULE}._init_client") as mock_init:
            mock_init.return_value = "client"
            from app.db.supabase_client import get_supabase_client
            get_supabase_client()
            get_supabase_client(refresh=True)
            assert mock_init.call_count == 2

    def test_get_supabase_db_raises_503_when_none(self):
        with patch(f"{self.MODULE}.get_supabase_client", return_value=None):
            from app.db.supabase_client import get_supabase_db
            with pytest.raises(Exception) as exc:
                get_supabase_db()
            assert "503" in str(exc.value) or exc.value.status_code == 503

    def test_get_supabase_db_returns_client(self):
        with patch(f"{self.MODULE}.get_supabase_client", return_value="client"):
            from app.db.supabase_client import get_supabase_db
            assert get_supabase_db() == "client"

    def test_check_supabase_health_unconfigured(self):
        with patch(f"{self.MODULE}.get_supabase_client", return_value=None):
            from app.db.supabase_client import check_supabase_health
            result = check_supabase_health()
            assert result["status"] == "unconfigured"

    def test_check_supabase_health_healthy(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = None
        with patch(f"{self.MODULE}.get_supabase_client", return_value=mock_client):
            from app.db.supabase_client import check_supabase_health
            result = check_supabase_health()
            assert result["status"] == "healthy"

    def test_check_supabase_health_unhealthy(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("db down")
        with patch(f"{self.MODULE}.get_supabase_client", return_value=mock_client):
            from app.db.supabase_client import check_supabase_health
            result = check_supabase_health()
            assert result["status"] == "unhealthy"
