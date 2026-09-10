"""Preserve legacy expense report visibility."""

from alembic import op
import sqlalchemy as sa

revision = "0006_expense_report_visibility"
down_revision = "0005_tenant_deposit_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("show_in_report", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_index("ix_expenses_show_in_report", "expenses", ["show_in_report"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expenses_show_in_report", table_name="expenses")
    op.drop_column("expenses", "show_in_report")
