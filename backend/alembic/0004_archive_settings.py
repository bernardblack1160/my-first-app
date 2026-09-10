"""Add durable archive and settings stores used by the working app.

Revision ID: 0004_archive_settings
Revises: 0003_canonical_transactions
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_archive_settings"
down_revision = "0003_canonical_transactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("total_income", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_expense", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("balance", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "title", name="ix_archives_workspace_title"),
    )
    op.create_index("ix_archives_workspace_id", "archives", ["workspace_id"])
    op.create_table(
        "settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("value", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "key", name="ix_settings_workspace_key"),
    )
    op.create_index("ix_settings_workspace_id", "settings", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_settings_workspace_id", table_name="settings")
    op.drop_table("settings")
    op.drop_index("ix_archives_workspace_id", table_name="archives")
    op.drop_table("archives")
