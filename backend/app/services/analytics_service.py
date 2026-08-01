"""
Analytics service for tracking user events.
Uses PostHog when configured, falls back to structured logging.
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self):
        self._posthog = None
        self._api_key = os.environ.get("POSTHOG_API_KEY", "")
        self._host = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
        self._enabled = bool(self._api_key)

        if self._enabled:
            try:
                from posthog import Posthog

                self._posthog = Posthog(
                    project_api_key=self._api_key,
                    host=self._host,
                    debug=False,
                )
                logger.info("PostHog analytics initialized")
            except Exception as e:
                logger.warning("PostHog initialization failed, using log-only analytics: %s", e)
                self._enabled = False

    def capture(self, distinct_id: str, event: str, properties: dict[str, Any] | None = None):
        """Capture an analytics event."""
        if self._enabled and self._posthog:
            try:
                self._posthog.capture(
                    distinct_id=distinct_id,
                    event=event,
                    properties=properties or {},
                )
            except Exception as e:
                logger.warning("Analytics capture failed: %s", e)

        logger.info(
            "Analytics event: %s [user=%s, props=%s]",
            event,
            distinct_id[:8] if distinct_id else "anonymous",
            properties,
        )


analytics_service = AnalyticsService()
