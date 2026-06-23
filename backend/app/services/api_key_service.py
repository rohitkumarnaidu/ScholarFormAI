# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
API Key CRUD service for managing user-provided LLM provider keys.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.api_key import UserApiKey
from app.models.api_key_usage_log import ApiKeyUsageLog
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {
    "openai": {"name": "OpenAI", "default_rpm": 60, "default_rph": 1000, "default_daily": 10000},
    "anthropic": {"name": "Anthropic", "default_rpm": 50, "default_rph": 800, "default_daily": 8000},
    "deepseek": {"name": "DeepSeek", "default_rpm": 60, "default_rph": 1000, "default_daily": 10000},
    "groq": {"name": "Groq", "default_rpm": 30, "default_rph": 600, "default_daily": 6000},
    "google": {"name": "Google AI", "default_rpm": 60, "default_rph": 1000, "default_daily": 10000},
    "cohere": {"name": "Cohere", "default_rpm": 40, "default_rph": 800, "default_daily": 8000},
    "mistral": {"name": "Mistral", "default_rpm": 60, "default_rph": 1000, "default_daily": 10000},
}


class ApiKeyService:
    """CRUD operations for user API keys."""

    def __init__(self, db: Session):
        self.db = db
        self.encryption = get_encryption_service()

    def create_key(
        self,
        user_id: str,
        provider: str,
        api_key: str,
        key_label: Optional[str] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
        daily_quota: Optional[int] = None,
    ) -> UserApiKey:
        provider_lower = provider.lower()
        if provider_lower not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}. Supported: {list(SUPPORTED_PROVIDERS.keys())}")

        provider_defaults = SUPPORTED_PROVIDERS[provider_lower]
        encrypted_key = self.encryption.encrypt(api_key)

        new_key = UserApiKey(
            user_id=user_id,
            provider=provider_lower,
            api_key_encrypted=encrypted_key,
            key_label=key_label or f"{provider_defaults['name']} Key",
            rate_limit_per_minute=rate_limit_per_minute or provider_defaults["default_rpm"],
            rate_limit_per_hour=rate_limit_per_hour or provider_defaults["default_rph"],
            daily_quota=daily_quota or provider_defaults["default_daily"],
        )
        self.db.add(new_key)
        self.db.commit()
        self.db.refresh(new_key)
        logger.info("Created API key for user %s, provider %s", user_id, provider_lower)
        return new_key

    def get_key(self, key_id: str, user_id: str) -> Optional[UserApiKey]:
        result = self.db.execute(
            select(UserApiKey).where(
                and_(UserApiKey.id == key_id, UserApiKey.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    def get_active_key(self, user_id: str, provider: str) -> Optional[UserApiKey]:
        result = self.db.execute(
            select(UserApiKey).where(
                and_(
                    UserApiKey.user_id == user_id,
                    UserApiKey.provider == provider.lower(),
                    UserApiKey.is_active == True,
                )
            ).order_by(UserApiKey.updated_at.desc())
        )
        return result.scalar_one_or_none()

    def list_keys(self, user_id: str, provider: Optional[str] = None) -> list[UserApiKey]:
        query = select(UserApiKey).where(UserApiKey.user_id == user_id)
        if provider:
            query = query.where(UserApiKey.provider == provider.lower())
        query = query.order_by(UserApiKey.created_at.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    def update_key(
        self,
        key_id: str,
        user_id: str,
        key_label: Optional[str] = None,
        is_active: Optional[bool] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
        daily_quota: Optional[int] = None,
    ) -> Optional[UserApiKey]:
        key = self.get_key(key_id, user_id)
        if not key:
            return None

        if key_label is not None:
            key.key_label = key_label
        if is_active is not None:
            key.is_active = is_active
        if rate_limit_per_minute is not None:
            key.rate_limit_per_minute = rate_limit_per_minute
        if rate_limit_per_hour is not None:
            key.rate_limit_per_hour = rate_limit_per_hour
        if daily_quota is not None:
            key.daily_quota = daily_quota

        key.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(key)
        return key

    def delete_key(self, key_id: str, user_id: str) -> bool:
        key = self.get_key(key_id, user_id)
        if not key:
            return False
        self.db.delete(key)
        self.db.commit()
        logger.info("Deleted API key %s for user %s", key_id, user_id)
        return True

    def decrypt_key(self, key: UserApiKey) -> str:
        """Decrypt and return the raw API key value."""
        return self.encryption.decrypt(key.api_key_encrypted)

    def increment_usage(self, key_id: str) -> None:
        """Increment total request count and update last_request_at."""
        result = self.db.execute(
            select(UserApiKey).where(UserApiKey.id == key_id)
        )
        key = result.scalar_one_or_none()
        if key:
            key.total_requests += 1
            key.last_request_at = datetime.now(timezone.utc)
            self.db.commit()

    def log_usage(
        self,
        user_api_key_id: str,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        status_code: Optional[int] = None,
        response_time_ms: Optional[int] = None,
    ) -> None:
        """Log a single API key usage event."""
        log_entry = ApiKeyUsageLog(
            user_api_key_id=user_api_key_id,
            endpoint=endpoint,
            model=model,
            tokens_used=tokens_used,
            status_code=status_code,
            response_time_ms=response_time_ms,
        )
        self.db.add(log_entry)
        self.db.commit()

    def get_usage_stats(
        self,
        user_id: str,
        hours: int = 24,
    ) -> dict:
        """Get usage statistics for a user's API keys over the last N hours."""
        cutoff = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(hours=hours)

        result = self.db.execute(
            select(
                UserApiKey.provider,
                func.count(ApiKeyUsageLog.id).label("total_requests"),
                func.sum(ApiKeyUsageLog.tokens_used).label("total_tokens"),
                func.avg(ApiKeyUsageLog.response_time_ms).label("avg_response_time"),
            )
            .join(ApiKeyUsageLog, UserApiKey.id == ApiKeyUsageLog.user_api_key_id)
            .where(
                and_(
                    UserApiKey.user_id == user_id,
                    ApiKeyUsageLog.created_at >= cutoff,
                )
            )
            .group_by(UserApiKey.provider)
        )
        rows = result.all()

        stats = {}
        for row in rows:
            stats[row.provider] = {
                "total_requests": row.total_requests or 0,
                "total_tokens": row.total_tokens or 0,
                "avg_response_time_ms": round(float(row.avg_response_time), 2) if row.avg_response_time else 0,
            }
        return stats

    @staticmethod
    def get_supported_providers() -> dict:
        return SUPPORTED_PROVIDERS
