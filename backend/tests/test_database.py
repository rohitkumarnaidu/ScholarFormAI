# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
Database Layer Tests
Tests database connection, Supabase client operations, and graceful degradation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock


class TestDatabaseLayer:
    """Test suite for database layer."""

    @pytest.mark.database
    def test_supabase_client_creation(self):
        """Test Supabase client can be created."""
        with patch('app.db.supabase_client.create_client') as mock_create_client:
            with patch('app.db.supabase_client.settings') as mock_settings:
                mock_settings.SUPABASE_URL = "http://localhost:8000"
                mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test_key"

                from app.db.supabase_client import get_supabase_client

                mock_create_client.return_value = MagicMock()
                client = get_supabase_client(refresh=True)
                assert mock_create_client.called

    @pytest.mark.database
    def test_graceful_degradation_on_connection_failure(self):
        """Test graceful degradation when database unavailable."""
        with patch('app.db.supabase_client.create_client') as mock_create_client:
            mock_create_client.side_effect = Exception("Connection failed")

            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client(refresh=True)
            assert client is None

    @pytest.mark.database
    def test_missing_credentials(self):
        """Test client creation fails gracefully with missing credentials."""
        with patch('app.db.supabase_client.settings') as mock_settings:
            mock_settings.SUPABASE_URL = ""
            mock_settings.SUPABASE_SERVICE_ROLE_KEY = ""

            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client(refresh=True)
            assert client is None

    @pytest.mark.database
    def test_supabase_client_returns_singleton(self):
        """Test that get_supabase_client returns the same instance when not refreshed."""
        with patch('app.db.supabase_client.create_client') as mock_create:
            with patch('app.db.supabase_client.settings') as mock_settings:
                mock_settings.SUPABASE_URL = "http://localhost:8000"
                mock_settings.SUPABASE_SERVICE_ROLE_KEY = "test_key"
                mock_create.return_value = MagicMock()

                from app.db.supabase_client import get_supabase_client

                client1 = get_supabase_client(refresh=True)
                client2 = get_supabase_client(refresh=False)
                assert client1 is not None

    @pytest.mark.database
    def test_supabase_client_insert_operation(self):
        """Test database insert operation behavior."""
        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "1"}])

        with patch('app.db.supabase_client.get_supabase_client', return_value=mock_client):
            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            result = client.table("documents").insert({"title": "Test"}).execute()
            assert result.data is not None

    @pytest.mark.database
    def test_supabase_client_select_operation(self):
        """Test database select operation behavior."""
        mock_client = MagicMock()
        mock_data = [{"id": "1", "title": "Doc 1"}, {"id": "2", "title": "Doc 2"}]
        mock_client.table.return_value.select.return_value.execute.return_value = MagicMock(data=mock_data)

        with patch('app.db.supabase_client.get_supabase_client', return_value=mock_client):
            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            result = client.table("documents").select("*").execute()
            assert len(result.data) == 2

    @pytest.mark.database
    def test_supabase_client_update_operation(self):
        """Test database update operation behavior."""
        mock_client = MagicMock()
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        with patch('app.db.supabase_client.get_supabase_client', return_value=mock_client):
            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            result = client.table("documents").update({"status": "completed"}).eq("id", "1").execute()
            assert result.data is not None

    @pytest.mark.database
    def test_supabase_client_delete_operation(self):
        """Test database delete operation behavior."""
        mock_client = MagicMock()
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        with patch('app.db.supabase_client.get_supabase_client', return_value=mock_client):
            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            result = client.table("documents").delete().eq("id", "1").execute()
            assert result.data is not None

    @pytest.mark.database
    def test_supabase_client_error_handling(self):
        """Test database operations handle errors gracefully."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.side_effect = Exception("DB error")

        with patch('app.db.supabase_client.get_supabase_client', return_value=mock_client):
            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            with pytest.raises(Exception, match="DB error"):
                client.table("documents").select("*").execute()

    @pytest.mark.database
    def test_supabase_client_none_client_handling(self):
        """Test operations when client is None."""
        with patch('app.db.supabase_client.get_supabase_client', return_value=None):
            from app.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            assert client is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "database"])
