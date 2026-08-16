"""add notification system

Revision ID: 3237de8a80a8
Revises: 20260814_0001
Create Date: 2026-08-14 16:16:35.071832

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "3237de8a80a8"
down_revision: Union[str, Sequence[str], None] = "20260814_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("channel_preferences", postgresql.JSONB, server_default="{}"),
        sa.Column("dnd_enabled", sa.Boolean(), server_default="false"),
        sa.Column("dnd_start_time", sa.String(), nullable=True),
        sa.Column("dnd_end_time", sa.String(), nullable=True),
        sa.Column("timezone", sa.String(), server_default="UTC"),
        sa.Column("digest_mode", sa.String(), server_default="none"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.String(), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, server_default="{}"),
        sa.Column("status", sa.String(), server_default="pending", index=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("retry_count", sa.String(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("notification_preferences")
