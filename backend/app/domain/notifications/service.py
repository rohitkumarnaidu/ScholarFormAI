import json
import logging
import uuid
from typing import Dict, Any, List

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.config.settings import settings

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def _evaluate_preferences(db: Session, user_id: uuid.UUID, notif_type: str) -> Dict[str, bool]:
        """
        Determines which channels are active for a specific user and notification type.
        Returns a dict e.g. {"email": True, "slack": False, "in_app": True}
        """
        prefs = db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        ).scalar_one_or_none()

        # Default behavior if no preferences set
        if not prefs:
            return {"in_app": True, "email": True, "push": False, "slack": False, "discord": False}

        if prefs.dnd_enabled:
            # We would add actual time checking here based on timezone
            pass

        channel_prefs = prefs.channel_preferences or {}
        active_channels = {}
        for channel in ["in_app", "email", "push", "sms", "slack", "discord", "teams", "webhook"]:
            channel_opts = channel_prefs.get(channel, {})
            # If the user explicitly sets the whole channel to False, respect it.
            if channel_opts is False:
                active_channels[channel] = False
                continue

            # If not explicitly false, assume true for in_app and email for critical types
            if channel in ["in_app", "email"] and not channel_opts:
                active_channels[channel] = True
            elif isinstance(channel_opts, dict):
                active_channels[channel] = channel_opts.get(notif_type, False)
            else:
                active_channels[channel] = bool(channel_opts)

        return active_channels

    @staticmethod
    async def dispatch(db: Session, user_id: uuid.UUID, notif_type: str, title: str, body: str, metadata: Dict = None):
        """
        Dispatches a notification to all allowed channels.
        """
        if not metadata:
            metadata = {}

        channels = NotificationService._evaluate_preferences(db, user_id, notif_type)

        # Check digest mode from preferences
        prefs = db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        ).scalar_one_or_none()
        digest_active = prefs and prefs.digest_mode in ["daily", "weekly"]

        # Always create in-app notification if they haven't explicitly disabled it
        if channels.get("in_app", True):
            notif = Notification(
                user_id=user_id, type=notif_type, title=title, body=body, metadata_json=metadata, status="pending"
            )
            db.add(notif)
            db.commit()
            db.refresh(notif)

            # Emit to WebSocket/SSE
            from app.routers.v1.stream import emit_event

            emit_event(
                str(user_id),
                "notification_received",
                {"id": str(notif.id), "title": title, "body": body, "type": notif_type},
            )

            notif.status = "sent"
            db.commit()

        # Mock dispatch for third party integrations
        if digest_active:
            logger.info(f"Notification held for digest: {title}")
            return

        if channels.get("slack"):
            await NotificationService._dispatch_slack(title, body)

        if channels.get("email"):
            await NotificationService._dispatch_email(user_id, title, body)

    @staticmethod
    async def _dispatch_slack(title: str, body: str):
        # Mock slack webhook post
        logger.info(f"Dispatched to Slack: {title}")

    @staticmethod
    async def _dispatch_email(user_id: uuid.UUID, title: str, body: str):
        # Mock email via SendGrid/SMTP
        logger.info(f"Dispatched Email to {user_id}: {title}")
