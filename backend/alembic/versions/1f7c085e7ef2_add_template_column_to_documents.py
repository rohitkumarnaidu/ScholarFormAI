# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ScholarForm AI

"""add_template_column_to_documents

Revision ID: 1f7c085e7ef2
Revises: 5ab5f4f9e36d
Create Date: 2026-02-13 19:46:48.331380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f7c085e7ef2'
down_revision: Union[str, Sequence[str], None] = '5ab5f4f9e36d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add template column with NULL as default (idempotent for drifted DBs)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("documents")}
    if "template" not in existing:
        op.add_column('documents', sa.Column('template', sa.String(), nullable=True, server_default=None))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove template column (idempotent for drifted DBs)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("documents")}
    if "template" in existing:
        op.drop_column('documents', 'template')
