"""Use the working app's transaction model as the single payment source.

Revision ID: 0003_canonical_transactions
Revises: 0002_finance_features
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_canonical_transactions"
down_revision = "0002_finance_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("kind", sa.String(length=20), server_default="rent", nullable=False),
        sa.Column("show_in_report", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("settled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("type", sa.String(length=20), server_default="income", nullable=False),
        sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_workspace_id", "transactions", ["workspace_id"])
    op.create_index("ix_transactions_tenant_id", "transactions", ["tenant_id"])
    op.create_index("ix_transactions_archived", "transactions", ["archived"])
    op.create_index("ix_transactions_workspace_date", "transactions", ["workspace_id", "date"])
    op.create_index("ix_transactions_tenant_date", "transactions", ["tenant_id", "date"])
    op.execute(
        sa.text(
            "INSERT INTO transactions (id, workspace_id, tenant_id, date, amount, description, kind, show_in_report, settled, type, archived) "
            "SELECT p.id, t.workspace_id, p.tenant_id, p.paid_on, p.amount, p.note, 'rent', true, true, 'income', false "
            "FROM payments p JOIN tenants t ON t.id = p.tenant_id"
        )
    )
    op.drop_table("payments")


def downgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO payments (id, tenant_id, paid_on, amount, note) "
            "SELECT id, tenant_id, date, amount, description FROM transactions WHERE kind = 'rent' AND type = 'income'"
        )
    )
    op.drop_index("ix_transactions_tenant_date", table_name="transactions")
    op.drop_index("ix_transactions_workspace_date", table_name="transactions")
    op.drop_index("ix_transactions_archived", table_name="transactions")
    op.drop_index("ix_transactions_tenant_id", table_name="transactions")
    op.drop_index("ix_transactions_workspace_id", table_name="transactions")
    op.drop_table("transactions")
