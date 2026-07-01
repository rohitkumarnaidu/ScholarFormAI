import pytest
from unittest.mock import MagicMock, patch


class TestCreateEngineSafe:
    def test_returns_none_when_no_db_url(self):
        with patch("app.db.session.settings.SUPABASE_DB_URL", None):
            from app.db.session import _create_engine_safe
            assert _create_engine_safe() is None

    def test_returns_none_when_empty_string(self):
        with patch("app.db.session.settings.SUPABASE_DB_URL", ""):
            from app.db.session import _create_engine_safe
            assert _create_engine_safe() is None

    def test_returns_engine_when_configured(self):
        with patch("app.db.session.settings.SUPABASE_DB_URL", "sqlite:///:memory:"):
            with patch("app.db.session.create_engine") as mock_create:
                mock_engine = MagicMock()
                mock_create.return_value = mock_engine
                from app.db.session import _create_engine_safe
                engine = _create_engine_safe()
                assert engine is mock_engine

    def test_handles_engine_creation_error(self):
        with patch("app.db.session.settings.SUPABASE_DB_URL", "bad://url"):
            with patch("app.db.session.create_engine") as mock_create:
                mock_create.side_effect = RuntimeError("engine fail")
                from app.db.session import _create_engine_safe
                assert _create_engine_safe() is None


class TestCheckDbHealth:
    def test_unconfigured(self):
        with patch("app.db.session.engine", None):
            from app.db.session import check_db_health
            result = check_db_health()
            assert result["status"] == "unconfigured"

    def test_healthy(self):
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        with patch("app.db.session.engine", mock_engine):
            from app.db.session import check_db_health
            result = check_db_health()
            assert result["status"] == "healthy"

    def test_unhealthy(self):
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = __import__("sqlalchemy").exc.OperationalError(
            "fake", None, None
        )
        with patch("app.db.session.engine", mock_engine):
            from app.db.session import check_db_health
            result = check_db_health()
            assert result["status"] == "unhealthy"


class TestGetDb:
    def test_yields_session_and_closes(self):
        from app.db.session import get_db
        mock_session = MagicMock()
        with patch("app.db.session.SessionLocal", return_value=mock_session):
            gen = get_db()
            session = next(gen)
            assert session is mock_session
            with pytest.raises(StopIteration):
                next(gen)
            mock_session.close.assert_called_once()
