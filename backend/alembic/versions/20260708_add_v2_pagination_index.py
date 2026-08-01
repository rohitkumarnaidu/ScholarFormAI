"""Add composite index for cursor-based pagination on documents

Revision ID: 20260708_add_v2_pagination_index
Revises: 20260708_0002_add_document_shares
Create Date: 2026-07-08 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "20260708_add_v2_pagination_index"
down_revision = "20260708_0002_add_document_shares"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_documents_user_created",
        "documents",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_documents_user_updated",
        "documents",
        ["user_id", sa.text("updated_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_documents_user_updated", table_name="documents")
    op.drop_index("idx_documents_user_created", table_name="documents")

__all__ = ['revision', 'down_revision', 'branch_labels', 'depends_on', 'upgrade', 'downgrade']
