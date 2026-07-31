# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""
SQLAlchemy Declarative Base.

All ORM models should inherit from `Base`.
Uses the modern `DeclarativeBase` API (SQLAlchemy 2.x compatible).
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base for all SQLAlchemy models.

    Switching from the legacy `declarative_base()` factory to the
    class-based `DeclarativeBase` removes the deprecation warning
    introduced in SQLAlchemy 2.0 and ensures forward compatibility.
    """

    pass
