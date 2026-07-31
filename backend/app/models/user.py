# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI


from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from app.db.base import Base


class User(Base):
    __tablename__ = "profiles"

    # We use the 'id' from auth.users, so it is a foreign key in concept,
    # but here we treat it as the primary key of our profile.
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email = Column(String, index=True)
    full_name = Column(String)
    institution = Column(String)
    role = Column(String, server_default="authenticated")
    plan_tier = Column(String, server_default="free")
    stripe_customer_id = Column(String)
    billing_status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    documents = relationship(
        "Document", back_populates="user", lazy="selectin", primaryjoin="User.id == foreign(Document.user_id)"
    )
    suggestions = relationship(
        "Suggestion", back_populates="user", lazy="selectin", primaryjoin="User.id == foreign(Suggestion.user_id)"
    )
    api_keys = relationship(
        "UserApiKey", back_populates="user", lazy="selectin", primaryjoin="User.id == foreign(UserApiKey.user_id)"
    )
    custom_providers = relationship(
        "CustomProvider",
        back_populates="user",
        lazy="selectin",
        primaryjoin="User.id == foreign(CustomProvider.user_id)",
    )
