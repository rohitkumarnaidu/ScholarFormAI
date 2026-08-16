# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""users_billing_fields

Revision ID: 20260315_0002
Revises: 20260315_0001
Create Date: 2026-03-15 12:05:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260315_0002"
down_revision: str | Sequence[str] | None = "20260315_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("profiles")}

    if "plan_tier" not in existing:
        op.add_column(
            "profiles",
            sa.Column("plan_tier", sa.Text(), nullable=False, server_default=sa.text("'free'")),
        )
    if "stripe_customer_id" not in existing:
        op.add_column(
            "profiles",
            sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        )
    if "billing_status" not in existing:
        op.add_column(
            "profiles",
            sa.Column("billing_status", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("profiles")}

    if "billing_status" in existing:
        op.drop_column("profiles", "billing_status")
    if "stripe_customer_id" in existing:
        op.drop_column("profiles", "stripe_customer_id")
    if "plan_tier" in existing:
        op.drop_column("profiles", "plan_tier")


__all__ = ["revision", "down_revision", "branch_labels", "depends_on", "upgrade", "downgrade"]
