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
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '530ab1236474'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
