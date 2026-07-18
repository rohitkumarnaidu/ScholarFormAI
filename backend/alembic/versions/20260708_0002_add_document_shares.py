"""add document shares table

Revision ID: 20260708_0002_add_document_shares
Revises: 20260708_add_performance_indexes
Create Date: 2026-07-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260708_0002_add_document_shares"
down_revision = "20260708_add_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shared_with_user_id", sa.String(), nullable=False),
        sa.Column("permission", sa.String(), nullable=False, server_default="view"),
        sa.Column("shared_by_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_document_shares_doc_id", "document_shares", ["document_id"])
    op.create_index("idx_document_shares_user_id", "document_shares", ["shared_with_user_id"])
    op.create_unique_constraint("uq_document_shares", "document_shares", ["document_id", "shared_with_user_id"])


def downgrade() -> None:
    op.drop_table("document_shares")
