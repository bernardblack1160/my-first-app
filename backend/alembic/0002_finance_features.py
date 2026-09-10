"""Add tenant archive, property expenses, and tenant obligations.

Revision ID: 0002_finance_features
Revises: 0001_initial
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_finance_features"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tenants_archived_at", "tenants", ["archived_at"], unique=False)
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("category", sa.String(length=80), server_default="سایر", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_expenses_workspace_id", "expenses", ["workspace_id"], unique=False)
    op.create_index("ix_expenses_workspace_date", "expenses", ["workspace_id", "spent_on"], unique=False)
    op.create_table(
        "obligations",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Uuid(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_obligations_workspace_id", "obligations", ["workspace_id"], unique=False)
    op.create_index("ix_obligations_tenant_id", "obligations", ["tenant_id"], unique=False)
    op.create_index("ix_obligations_workspace_due_date", "obligations", ["workspace_id", "due_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_obligations_workspace_due_date", table_name="obligations")
    op.drop_index("ix_obligations_tenant_id", table_name="obligations")
    op.drop_index("ix_obligations_workspace_id", table_name="obligations")
    op.drop_table("obligations")
    op.drop_index("ix_expenses_workspace_date", table_name="expenses")
    op.drop_index("ix_expenses_workspace_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_tenants_archived_at", table_name="tenants")
    op.drop_column("tenants", "archived_at")
