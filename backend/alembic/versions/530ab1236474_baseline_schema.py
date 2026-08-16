# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""baseline_schema

Baseline migration — schema is managed directly by Supabase.
This intentional no-op placeholder maintains Alembic revision history
compatibility so that future migrations can build on this baseline.

Revision ID: 530ab1236474
Revises:
Create Date: 2026-02-08 18:50:29.904227

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "530ab1236474"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass


__all__ = ["revision", "down_revision", "branch_labels", "depends_on", "upgrade", "downgrade"]
