import uuid
import pytest
from unittest.mock import MagicMock

from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.domain.notifications.service import NotificationService


@pytest.mark.asyncio
async def test_evaluate_preferences_default():
    user_id = uuid.uuid4()
    db_session = MagicMock()

    # Mock db.execute().scalar_one_or_none() to return None (no prefs)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db_session.execute.return_value = mock_result

    channels = NotificationService._evaluate_preferences(db_session, user_id, "security")
    assert channels.get("in_app") is True
    assert channels.get("email") is True
    assert channels.get("slack") is False


@pytest.mark.asyncio
async def test_evaluate_preferences_custom():
    user_id = uuid.uuid4()
    db_session = MagicMock()

    prefs = NotificationPreference(
        user_id=user_id, channel_preferences={"slack": {"security": True}, "email": {"security": False}}
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = prefs
    db_session.execute.return_value = mock_result

    channels = NotificationService._evaluate_preferences(db_session, user_id, "security")
    assert channels.get("in_app") is True  # Defaults to true if not overridden
    assert channels.get("email") is False
    assert channels.get("slack") is True


@pytest.mark.asyncio
async def test_digest_mode_holds_dispatch(monkeypatch):
    user_id = uuid.uuid4()
    db_session = MagicMock()

    prefs = NotificationPreference(
        user_id=user_id, digest_mode="daily", channel_preferences={"slack": {"billing": True}, "in_app": False}
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = prefs
    db_session.execute.return_value = mock_result

    # We'll monitor slack dispatch
    dispatched = []

    async def mock_dispatch_slack(title, body):
        dispatched.append(title)

    monkeypatch.setattr(NotificationService, "_dispatch_slack", mock_dispatch_slack)

    await NotificationService.dispatch(db_session, user_id, "billing", "Invoice Ready", "Body")

    # DB session should not add any in-app notification because in_app=False
    assert not db_session.add.called

    # But slack should NOT be dispatched because of digest mode
    assert len(dispatched) == 0
