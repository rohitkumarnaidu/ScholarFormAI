import logging
from unittest.mock import patch


class TestLoggingConfig:
    MODULE = "app.config.logging_config"

    def test_setup_logging_idempotent(self):
        with patch(f"{self.MODULE}._logging_initialized", False), \
             patch(f"{self.MODULE}.LOGGING_CONFIG", {"version": 1, "disable_existing_loggers": False, "formatters": {}, "handlers": {}, "loggers": {}}), \
             patch("logging.config.dictConfig") as mock_dict:
            from app.config.logging_config import setup_logging
            logger = setup_logging()
            assert logger.name == "app"
            mock_dict.assert_called_once()
            logger2 = setup_logging()
            assert logger2.name == "app"
            assert mock_dict.call_count == 1

    def test_setup_logging_fallback_on_error(self):
        with patch(f"{self.MODULE}._logging_initialized", False), \
             patch("logging.config.dictConfig", side_effect=Exception("config error")), \
             patch("logging.basicConfig") as mock_basic:
            from app.config.logging_config import setup_logging
            logger = setup_logging()
            assert logger.name == "app"
            mock_basic.assert_called_once_with(level=logging.INFO)

    def test_logs_dir_created(self):
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            import importlib

            import app.config.logging_config
            importlib.reload(app.config.logging_config)
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)

    def test_logs_dir_is_path(self):
        from pathlib import Path

        from app.config.logging_config import LOGS_DIR
        assert isinstance(LOGS_DIR, Path)
        assert "logs" in str(LOGS_DIR).lower()

    def test_logging_config_structure(self):
        from app.config.logging_config import LOGGING_CONFIG
        assert "version" in LOGGING_CONFIG
        assert "formatters" in LOGGING_CONFIG
        assert "handlers" in LOGGING_CONFIG
        assert "loggers" in LOGGING_CONFIG
        assert "console" in LOGGING_CONFIG["handlers"]
        assert "file" in LOGGING_CONFIG["handlers"]
        assert "error_file" in LOGGING_CONFIG["handlers"]
        assert "" in LOGGING_CONFIG["loggers"]
        assert "app" in LOGGING_CONFIG["loggers"]
