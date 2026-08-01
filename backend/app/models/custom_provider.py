import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class CustomProvider(Base):
    __tablename__ = "custom_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    models = Column(JSON, nullable=False, default=list)
    is_local = Column(Boolean, default=False, nullable=False)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    user = relationship(
        "User",
        back_populates="custom_providers",
        lazy="joined",
        primaryjoin="foreign(CustomProvider.user_id) == User.id",
    )

    def __init__(self, **kwargs):
        now = datetime.now(UTC)
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("models", [])
        kwargs.setdefault("is_local", False)
        kwargs.setdefault("is_active", True)
        kwargs.setdefault("created_at", now)
        kwargs.setdefault("updated_at", now)
        super().__init__(**kwargs)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "base_url": self.base_url,
            "models": self.models,
            "is_local": self.is_local,
            "description": self.description,
            "is_active": self.is_active,
            "api_key_encrypted": self.api_key_encrypted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
