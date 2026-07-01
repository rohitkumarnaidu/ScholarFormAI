import pytest
from unittest.mock import MagicMock, patch
from typing import Optional


class TestGetOrCreate:
    def test_creates_when_none(self):
        from app.utils.singleton import get_or_create

        factory = MagicMock(return_value="new_value")
        result = get_or_create(None, factory)
        assert result == "new_value"
        factory.assert_called_once()

    def test_returns_existing(self):
        from app.utils.singleton import get_or_create

        factory = MagicMock(return_value="should_not_be_called")
        result = get_or_create("existing", factory)
        assert result == "existing"
        factory.assert_not_called()


class TestGetOrCreateSafe:
    def test_creates_when_none(self):
        from app.utils.singleton import get_or_create_safe

        factory = MagicMock(return_value="new_value")
        logger = MagicMock()
        result = get_or_create_safe(None, factory, logger=logger, name="test_singleton")
        assert result == "new_value"

    def test_handles_exception(self):
        from app.utils.singleton import get_or_create_safe

        factory = MagicMock(side_effect=Exception("creation failed"))
        logger = MagicMock()
        result = get_or_create_safe(None, factory, logger=logger, name="test_singleton")
        assert result is None

    def test_returns_existing_value(self):
        from app.utils.singleton import get_or_create_safe

        factory = MagicMock(side_effect=Exception("should not be called"))
        logger = MagicMock()
        result = get_or_create_safe("existing", factory, logger=logger, name="test_singleton")
        assert result == "existing"


class TestGetOrCreateCatching:
    def test_creates_on_success(self):
        from app.utils.singleton import get_or_create_catching

        factory = MagicMock(return_value="new_value")
        result = get_or_create_catching(None, factory, exceptions=(Exception,))
        assert result == "new_value"

    def test_returns_none_on_failure(self):
        from app.utils.singleton import get_or_create_catching

        factory = MagicMock(side_effect=Exception("fail"))
        result = get_or_create_catching(None, factory, exceptions=(Exception,))
        assert result is None

    def test_returns_existing(self):
        from app.utils.singleton import get_or_create_catching

        factory = MagicMock(side_effect=Exception("should not be called"))
        result = get_or_create_catching("existing", factory, exceptions=(Exception,))
        assert result == "existing"


class TestResolveOptionalCallable:
    def test_none_module(self):
        from app.utils.singleton import resolve_optional_callable
        assert resolve_optional_callable("nonexistent.module", "func") is None

    def test_none_callable(self):
        from app.utils.singleton import resolve_optional_callable
        assert resolve_optional_callable("os", "nonexistent_func") is None

    def test_valid_callable(self):
        from app.utils.singleton import resolve_optional_callable
        result = resolve_optional_callable("os", "getcwd")
        assert isinstance(result, str)  # getcwd() returns a string
