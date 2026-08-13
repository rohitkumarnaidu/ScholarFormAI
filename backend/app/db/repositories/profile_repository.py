from __future__ import annotations

import logging
from typing import Any

from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ProfileRepository(BaseRepository):
    TABLE_NAME = "profiles"

    def get_user_id_by_stripe_customer_id(self, customer_id: str) -> str | None:
        """Fetch the internal user ID associated with a Stripe customer ID."""
        try:
            result = self._table().select("id").eq("stripe_customer_id", customer_id).maybe_single().execute()
            if result.data:
                return str(result.data["id"])
            return None
        except Exception as exc:
            logger.error("Failed to fetch user by Stripe customer ID: %s", exc)
            return None

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> bool:
        """Update a user's profile."""
        try:
            self._table().update(updates).eq("id", str(user_id)).execute()
            return True
        except Exception as exc:
            logger.error("Failed to update profile for %s: %s", user_id, exc)
            return False
